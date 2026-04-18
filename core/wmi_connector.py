"""WMI deep-scan connector for Windows hosts.

Connects to a remote Windows machine via DCOM/WMI and collects hardware and
OS details.  Requires the wmi and pywin32 packages, which are Windows-only;
the import is guarded so the module can be imported on any platform.

Prerequisites on the target host:
  - WMI service running
  - DCOM port 135 accessible through the firewall
  - Valid administrator credentials
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

try:
    import wmi as _wmi_module

    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False
    _wmi_module = None  # type: ignore[assignment]
    logger.warning("wmi module not available (non-Windows environment?)")


def scan(ip: str, username: str, password: str) -> dict[str, object]:
    """Collect hardware and OS details from a Windows host via WMI.

    Args:
        ip:       Target IP address.
        username: Domain\\username or local username (e.g. ``".\\Administrator"``).
        password: Plaintext password for the account.

    Returns:
        Dict with keys: hostname, os, ram_gb, cpu, serial, manufacturer, model.
        Returns an empty dict if WMI is unavailable or the connection fails.
    """
    if not WMI_AVAILABLE:
        logger.warning("wmi unavailable – skipping WMI scan for %s", ip)
        return {}

    try:
        c = _wmi_module.WMI(computer=ip, user=username, password=password)

        os_list = c.Win32_OperatingSystem()
        cs_list = c.Win32_ComputerSystem()
        bios_list = c.Win32_BIOS()
        proc_list = c.Win32_Processor()
        mem_list = c.Win32_PhysicalMemoryArray()

        if not (os_list and cs_list and bios_list and proc_list):
            logger.warning("WMI returned incomplete data for %s", ip)
            return {}

        os_info = os_list[0]
        cs_info = cs_list[0]
        bios_info = bios_list[0]
        proc_info = proc_list[0]

        ram_gb: int | None = None
        if mem_list:
            try:
                # MaxCapacity is in KB
                ram_gb = int(mem_list[0].MaxCapacity / (1024 * 1024))
            except (TypeError, ValueError):
                pass

        return {
            "hostname":     str(cs_info.Name or ""),
            "os":           str(os_info.Caption or ""),
            "ram_gb":       ram_gb,
            "cpu":          str(proc_info.Name or "").strip(),
            "serial":       str(bios_info.SerialNumber or ""),
            "manufacturer": str(cs_info.Manufacturer or ""),
            "model":        str(cs_info.Model or ""),
        }
    except Exception as exc:
        # WMI raises wmi.x_wmi and various COM exceptions; catch broadly
        logger.warning("WMI scan failed for %s: %s", ip, exc)
        return {}
