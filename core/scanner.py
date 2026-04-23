"""Scan orchestrator running as a QThread.

ScanWorker coordinates the full scan pipeline:
  1. ARP sweep (SendARP) to discover live hosts + MAC addresses
  2. MAC vendor lookup (OUI database)
  3. TCP port scan per host (pure Python sockets)
  4. Reverse-DNS hostname resolution
  5. Device type classification (ports + vendor + hostname)
  6. Optional deep scans: WMI, SSH, SNMP
     – Multiple credential sets are tried in order; the loop stops on first success.
     – WMI attempts have a hard timeout so a hanging DCOM connection does not
       prevent subsequent credential sets from being tried.
  7. Persists each Device to SQLite and emits signals for the UI
"""
from __future__ import annotations

import json
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from PyQt6.QtCore import QThread, pyqtSignal

from core import arp_sweep, device_classifier, port_scanner, vendor_lookup
from core.device_classifier import reclassify_from_scan
from core import snmp_connector, ssh_connector, wmi_connector
from data.credential_store import (
    SERVICE_SNMP,
    SERVICE_SSH,
    SERVICE_WMI,
    get_credentials_list,
)
from data.models import Device, DeviceType, Peripheral, ScanSession, ScanStatus

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """Background thread that runs the full network scan pipeline.

    Signals:
        progress(int, str):   Emitted periodically with (percent, message).
        device_found(object): Emitted once per discovered Device.
        finished():           Emitted when the scan has fully completed.
        error(str):           Emitted if a fatal scan-level error occurs.
    """

    progress     = pyqtSignal(int, str)
    device_found = pyqtSignal(object)
    finished     = pyqtSignal()
    error        = pyqtSignal(str)

    def __init__(
        self,
        session: ScanSession,
        config: dict,
        use_wmi:  bool = False,
        use_ssh:  bool = False,
        use_snmp: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._session  = session
        self._config   = config
        self._use_wmi  = use_wmi
        self._use_ssh  = use_ssh
        self._use_snmp = use_snmp
        self._abort    = False

    def abort(self) -> None:
        self._abort = True

    def run(self) -> None:
        try:
            self._run_scan()
        except Exception as exc:
            logger.exception("Unhandled exception in ScanWorker: %s", exc)
            self.error.emit(str(exc))
        finally:
            self.finished.emit()

    # ------------------------------------------------------------------
    # Scan pipeline
    # ------------------------------------------------------------------

    def _run_scan(self) -> None:
        mock_mode   = self._config.get("mock_mode", False)
        timeout     = self._config.get("scan_timeout", 2)
        max_workers = self._config.get("max_threads", 50)

        self.progress.emit(0, "Starte ARP-Sweep…")

        hosts = arp_sweep.sweep_mock() if mock_mode else arp_sweep.sweep(
            self._session.ip_range, timeout=timeout
        )

        if not hosts:
            self.progress.emit(100, "Keine Hosts gefunden.")
            return

        total = len(hosts)
        logger.info("%d host(s) found, starting port scans", total)

        with ThreadPoolExecutor(max_workers=min(max_workers, total)) as pool:
            futures = {pool.submit(self._scan_host, h): h for h in hosts}
            completed = 0
            for future in as_completed(futures):
                if self._abort:
                    break
                completed += 1
                pct = int(completed / total * 100)
                try:
                    device = future.result()
                except Exception as exc:
                    logger.error("Host scan raised: %s", exc)
                    device = None

                if device is not None:
                    self._session.devices.append(device)
                    self.device_found.emit(device)
                self.progress.emit(pct, f"Gescannt: {completed}/{total}")

        status = "Scan abgebrochen." if self._abort else "Scan abgeschlossen."
        self.progress.emit(100, status)

    # ------------------------------------------------------------------
    # Per-host scan
    # ------------------------------------------------------------------

    def _scan_host(self, host: dict[str, str]) -> Device | None:
        ip  = host["ip"]
        mac = host["mac"]
        mock_mode = self._config.get("mock_mode", False)

        vendor = vendor_lookup.lookup(mac) if not mock_mode else ""

        device = Device(
            session_id=self._session.id,
            ip=ip,
            mac=mac,
            manufacturer=vendor,
            scan_status=ScanStatus.SCANNING.value,
        )

        try:
            if mock_mode:
                _apply_mock_data(device)
            else:
                self._deep_scan(device, vendor)
            device.scan_status = ScanStatus.DONE.value
        except Exception as exc:
            logger.error("Error scanning %s: %s", ip, exc)
            device.scan_status = ScanStatus.FAILED.value

        # Auto-suggest a Monitor peripheral for CLIENT devices
        if device.device_type == DeviceType.CLIENT.value and not device.peripherals:
            device.peripherals.append(
                Peripheral(
                    device_id=device.id,
                    peripheral_type="Monitor",
                    is_suggestion=True,
                )
            )

        return device

    # ------------------------------------------------------------------
    # Deep scan
    # ------------------------------------------------------------------

    def _deep_scan(self, device: Device, vendor: str) -> None:
        ports = port_scanner.scan_ports(device.ip)

        # Reverse DNS – best-effort hostname before credential scans
        _resolve_hostname(device)

        # Device type classification
        device.device_type = device_classifier.classify(
            ports, device.hostname, vendor
        )

        # ── WMI (Windows) ──────────────────────────────────────────────
        if self._use_wmi and 135 in ports:
            wmi_creds = get_credentials_list(SERVICE_WMI)
            if not wmi_creds:
                logger.debug("No WMI credentials stored – skipping WMI for %s", device.ip)
            else:
                logger.info(
                    "Trying WMI on %s with %d credential set(s)", device.ip, len(wmi_creds)
                )
                for idx, (username, password) in enumerate(wmi_creds, 1):
                    logger.debug(
                        "WMI attempt %d/%d for %s (user: %s)",
                        idx, len(wmi_creds), device.ip, username,
                    )
                    data = wmi_connector.scan(device.ip, username, password)
                    if data:
                        logger.info(
                            "WMI succeeded on %s with credential set %d", device.ip, idx
                        )
                        _apply_dict(device, data)
                        reclassify_from_scan(device)
                        break
                    logger.debug(
                        "WMI credential set %d failed for %s – %s",
                        idx, device.ip,
                        "trying next" if idx < len(wmi_creds) else "no more credentials",
                    )

        # ── SSH (Linux / Unix) ─────────────────────────────────────────
        # Only try SSH if port 22 is open and host does NOT look like Windows
        if self._use_ssh and 22 in ports and 135 not in ports:
            ssh_creds = get_credentials_list(SERVICE_SSH)
            if not ssh_creds:
                logger.debug("No SSH credentials stored – skipping SSH for %s", device.ip)
            else:
                logger.info(
                    "Trying SSH on %s with %d credential set(s)", device.ip, len(ssh_creds)
                )
                for idx, (encoded_user, password) in enumerate(ssh_creds, 1):
                    # Support "user|/path/to/key" notation for key-based auth
                    if "|" in encoded_user:
                        username, key_path = encoded_user.split("|", 1)
                    else:
                        username, key_path = encoded_user, None

                    logger.debug(
                        "SSH attempt %d/%d for %s (user: %s, key: %s)",
                        idx, len(ssh_creds), device.ip, username, key_path or "password",
                    )
                    data = ssh_connector.scan(
                        device.ip,
                        username,
                        password=password or None,
                        key_path=key_path or None,
                    )
                    if data:
                        logger.info(
                            "SSH succeeded on %s with credential set %d", device.ip, idx
                        )
                        _apply_dict(device, data)
                        reclassify_from_scan(device)
                        break
                    logger.debug(
                        "SSH credential set %d failed for %s – %s",
                        idx, device.ip,
                        "trying next" if idx < len(ssh_creds) else "no more credentials",
                    )

        # ── SNMP (switches, printers, routers) ─────────────────────────
        if self._use_snmp and 161 in ports:
            snmp_creds = get_credentials_list(SERVICE_SNMP)
            # Fall back to config community string if nothing stored
            if not snmp_creds:
                default_community = self._config.get("snmp_community", "public")
                snmp_creds = [("", default_community)]

            logger.info(
                "Trying SNMP on %s with %d community string(s)", device.ip, len(snmp_creds)
            )
            for idx, (_, community) in enumerate(snmp_creds, 1):
                logger.debug(
                    "SNMP attempt %d/%d for %s (community: %s)",
                    idx, len(snmp_creds), device.ip, community,
                )
                data = snmp_connector.scan(device.ip, community)
                if data:
                    logger.info("SNMP succeeded on %s with community set %d", device.ip, idx)
                    if "sysDescr" in data and not device.os:
                        device.os = str(data["sysDescr"])
                    if "sysName" in data and not device.hostname:
                        device.hostname = str(data["sysName"])
                    break
                logger.debug(
                    "SNMP community set %d failed for %s – %s",
                    idx, device.ip,
                    "trying next" if idx < len(snmp_creds) else "no more community strings",
                )

        # Keep manufacturer from deep scan if richer; fall back to vendor lookup
        if not device.manufacturer:
            device.manufacturer = vendor

        device.raw_data = json.dumps({"open_ports": ports})


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _resolve_hostname(device: Device) -> None:
    """Try reverse DNS; only stores if we get a non-generic result."""
    if device.hostname:
        return  # already set (e.g. from a previous session)
    try:
        name = socket.gethostbyaddr(device.ip)[0]
        # Skip generic results like "192-168-1-10.provider.net"
        if name and not name.replace(".", "").replace("-", "").isdigit():
            device.hostname = name
    except (socket.herror, socket.gaierror, OSError):
        pass


def _apply_dict(device: Device, data: dict[str, object]) -> None:
    """Apply scan result dict to device, skipping empty/None values."""
    for key, value in data.items():
        if hasattr(device, key) and value is not None and value != "":
            setattr(device, key, value)


# ------------------------------------------------------------------
# Mock data (used when mock_mode = true in config)
# ------------------------------------------------------------------

_MOCK_PRESETS = [
    {"hostname": "PC-OFFICE-01",   "device_type": "C__OBJTYPE__CLIENT",
     "os": "Windows 11 Pro",       "manufacturer": "Dell",
     "model": "OptiPlex 7090",     "serial": "SN0001", "ram_gb": 16,
     "cpu": "Intel Core i7-10700"},
    {"hostname": "SRV-DC-01",      "device_type": "C__OBJTYPE__SERVER",
     "os": "Windows Server 2022",  "manufacturer": "HP",
     "model": "ProLiant DL380",    "serial": "SN0002", "ram_gb": 64,
     "cpu": "Intel Xeon Gold 6226R"},
    {"hostname": "SRV-FILE-01",    "device_type": "C__OBJTYPE__SERVER",
     "os": "Ubuntu 22.04 LTS",     "manufacturer": "Fujitsu",
     "model": "PRIMERGY RX300",    "serial": "SN0003", "ram_gb": 32,
     "cpu": "Intel Xeon E-2288G"},
    {"hostname": "SWITCH-CORE-01", "device_type": "C__OBJTYPE__SWITCH",
     "os": "Cisco IOS 15.2",       "manufacturer": "Cisco",
     "model": "Catalyst 2960X",    "serial": "SN0004"},
    {"hostname": "PRINTER-01",     "device_type": "C__OBJTYPE__PRINTER",
     "os": "",                      "manufacturer": "HP",
     "model": "LaserJet M507dn",   "serial": "SN0005"},
]


def _apply_mock_data(device: Device) -> None:
    import ipaddress
    try:
        last_octet = int(ipaddress.ip_address(device.ip)) & 0xFF
    except ValueError:
        last_octet = 0
    preset = _MOCK_PRESETS[last_octet % len(_MOCK_PRESETS)]
    _apply_dict(device, preset)
