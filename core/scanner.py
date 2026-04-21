"""Scan orchestrator running as a QThread.

ScanWorker coordinates the full scan pipeline:
  1. ARP sweep (SendARP) to discover live hosts + MAC addresses
  2. MAC vendor lookup (OUI database)
  3. TCP port scan per host (pure Python sockets)
  4. Device type classification (ports + vendor + hostname)
  5. Optional deep scans: WMI, SSH, SNMP – multiple credentials tried in order
  6. Persists each Device to SQLite and emits signals for the UI
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from PyQt6.QtCore import QThread, pyqtSignal

from core import arp_sweep, device_classifier, port_scanner, vendor_lookup
from core import snmp_connector, ssh_connector, wmi_connector
from data.credential_store import (
    SERVICE_SNMP,
    SERVICE_SSH,
    SERVICE_WMI,
    get_credentials_list,
)
from data.models import Device, ScanSession, ScanStatus
from data.session_store import SessionStore

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """Background thread that runs the full network scan pipeline.

    Signals:
        progress(int, str):   Emitted periodically with (percent, message).
        device_found(object): Emitted once per discovered Device.
        finished():           Emitted when the scan has fully completed.
        error(str):           Emitted if a fatal scan-level error occurs.
    """

    progress    = pyqtSignal(int, str)
    device_found = pyqtSignal(object)
    finished    = pyqtSignal()
    error       = pyqtSignal(str)

    def __init__(
        self,
        session: ScanSession,
        config: dict,
        use_wmi: bool = False,
        use_ssh: bool = False,
        use_snmp: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._session  = session
        self._config   = config
        self._use_wmi  = use_wmi
        self._use_ssh  = use_ssh
        self._use_snmp = use_snmp
        self._store    = SessionStore()
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

    def _scan_host(self, host: dict[str, str]) -> Device | None:
        ip  = host["ip"]
        mac = host["mac"]
        mock_mode = self._config.get("mock_mode", False)

        # Resolve vendor from MAC immediately
        vendor = vendor_lookup.lookup(mac) if not mock_mode else ""

        device = Device(
            session_id=self._session.id,
            ip=ip,
            mac=mac,
            manufacturer=vendor,   # early best-guess; overwritten by WMI/SSH if available
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

        self._store.save_device(device)
        return device

    def _deep_scan(self, device: Device, vendor: str) -> None:
        ports = port_scanner.scan_ports(device.ip)

        # Try reverse DNS for hostname
        try:
            device.hostname = __import__("socket").gethostbyaddr(device.ip)[0]
        except Exception:
            pass

        device.device_type = device_classifier.classify(
            ports, device.hostname, vendor
        )

        # WMI – try all stored credentials in order
        if self._use_wmi and 135 in ports:
            for username, password in get_credentials_list(SERVICE_WMI):
                data = wmi_connector.scan(device.ip, username, password)
                if data:
                    _apply_dict(device, data)
                    break

        # SSH – try all stored credentials in order
        if self._use_ssh and 22 in ports and 135 not in ports:
            for encoded_user, password in get_credentials_list(SERVICE_SSH):
                if "|" in encoded_user:
                    username, key_path = encoded_user.split("|", 1)
                else:
                    username, key_path = encoded_user, None
                data = ssh_connector.scan(
                    device.ip,
                    username,
                    password=password or None,
                    key_path=key_path or None,
                )
                if data:
                    _apply_dict(device, data)
                    break

        # SNMP
        if self._use_snmp and 161 in ports:
            snmp_creds = get_credentials_list(SERVICE_SNMP)
            community = snmp_creds[0][1] if snmp_creds else self._config.get(
                "snmp_community", "public"
            )
            data = snmp_connector.scan(device.ip, community)
            if "sysDescr" in data and not device.os:
                device.os = data["sysDescr"]
            if "sysName" in data and not device.hostname:
                device.hostname = data["sysName"]

        # Keep manufacturer from WMI/SSH if richer; fall back to vendor lookup
        if not device.manufacturer:
            device.manufacturer = vendor

        device.raw_data = json.dumps({"open_ports": ports})


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _apply_dict(device: Device, data: dict[str, object]) -> None:
    for key, value in data.items():
        if hasattr(device, key) and value:
            setattr(device, key, value)


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
