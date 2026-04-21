"""WMI deep-scan connector for Windows hosts.

Connects to a remote Windows machine via DCOM/WMI and collects hardware and
OS details.  Requires the wmi and pywin32 packages, which are Windows-only;
the import is guarded so the module can be imported on any platform.

Each scan attempt runs in a separate thread with a hard timeout so that a
hanging DCOM handshake (wrong credentials, firewall issues) does not block the
scan worker indefinitely and the next credential set can be tried.

Prerequisites on the target host:
  - WMI service running (winmgmt)
  - DCOM port 135 accessible through the firewall
  - Valid administrator credentials
"""
from __future__ import annotations

import concurrent.futures
import logging

logger = logging.getLogger(__name__)

try:
    import wmi as _wmi_module
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False
    _wmi_module = None  # type: ignore[assignment]
    logger.warning("wmi module not available (non-Windows environment?)")

# Seconds to wait for a WMI connection before giving up and trying next creds
_WMI_CONNECT_TIMEOUT = 20


def scan(ip: str, username: str, password: str) -> dict[str, object]:
    """Collect hardware and OS details from a Windows host via WMI.

    Wraps the actual WMI call in a thread with a hard timeout so a hanging
    DCOM connection does not block the scan worker.

    Args:
        ip:       Target IP address.
        username: Domain\\username or local username (e.g. ``.\\Administrator``).
        password: Plaintext password for the account.

    Returns:
        Dict with keys: hostname, os, ram_gb, cpu, serial, manufacturer, model.
        Returns an empty dict if WMI is unavailable, the connection times out,
        or any error occurs – so the caller can safely try the next credential.
    """
    if not WMI_AVAILABLE:
        logger.warning("wmi unavailable – skipping WMI scan for %s", ip)
        return {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do_wmi_scan, ip, username, password)
        try:
            return future.result(timeout=_WMI_CONNECT_TIMEOUT)
        except concurrent.futures.TimeoutError:
            logger.warning(
                "WMI connection timed out after %ds for %s (user: %s) – trying next credential",
                _WMI_CONNECT_TIMEOUT, ip, username,
            )
            return {}
        except Exception as exc:
            logger.warning("WMI scan failed for %s (user: %s): %s", ip, username, exc)
            return {}


def _do_wmi_scan(ip: str, username: str, password: str) -> dict[str, object]:
    """Perform the actual WMI queries – called inside a timeout-guarded thread."""
    try:
        c = _wmi_module.WMI(computer=ip, user=username, password=password)

        os_list   = c.Win32_OperatingSystem()
        cs_list   = c.Win32_ComputerSystem()
        bios_list = c.Win32_BIOS()
        proc_list = c.Win32_Processor()
        mem_list  = c.Win32_PhysicalMemoryArray()

        if not (os_list and cs_list and bios_list and proc_list):
            logger.warning("WMI returned incomplete data for %s", ip)
            return {}

        os_info   = os_list[0]
        cs_info   = cs_list[0]
        bios_info = bios_list[0]
        proc_info = proc_list[0]

        ram_gb: int | None = None
        if mem_list:
            try:
                # MaxCapacity is in KB
                ram_gb = int(mem_list[0].MaxCapacity / (1024 * 1024))
            except (TypeError, ValueError):
                pass

        result = {
            "hostname":     str(cs_info.Name or "").strip(),
            "os":           str(os_info.Caption or "").strip(),
            "ram_gb":       ram_gb,
            "cpu":          str(proc_info.Name or "").strip(),
            "serial":       str(bios_info.SerialNumber or "").strip(),
            "manufacturer": str(cs_info.Manufacturer or "").strip(),
            "model":        str(cs_info.Model or "").strip(),
        }
        logger.info("WMI scan succeeded for %s (host: %s)", ip, result.get("hostname"))
        return result

    except Exception as exc:
        # wmi raises wmi.x_wmi, x_access_denied and various COM exceptions
        logger.warning("WMI query error for %s (user: %s): %s", ip, username, exc)
        return {}
