"""Port-, vendor- and OS-based device type classifier.

Two-phase classification:
  1. classify()             – runs immediately after the port scan (before deep scan)
                              uses open ports, MAC vendor and hostname
  2. reclassify_from_scan() – runs after the deep scan when the OS string is known;
                              refines the result based on the actual operating system
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

PORT_SSH     = 22
PORT_WMI     = 135
PORT_SMB     = 445
PORT_SNMP    = 161
PORT_RDP     = 3389
PORT_PRINTER = 9100
PORT_HTTP    = 80
PORT_HTTPS   = 443

_SERVER_HOST_RE = re.compile(
    r"\b(srv|server|dc|ad|nas|esxi|vcenter|pdc|bdc|exchange|mail|backup|sql|db|web|app|prod|mgmt)\b",
    re.IGNORECASE,
)
_PRINTER_VENDOR_RE = re.compile(
    r"(kyocera|ricoh|canon|xerox|brother|konica|lexmark|epson|oki|sharp|bizhub)",
    re.IGNORECASE,
)
_SWITCH_VENDOR_RE = re.compile(
    r"(cisco|juniper|aruba|ubiquiti|netgear|tp.?link|mikrotik|extreme|brocade|ruckus)",
    re.IGNORECASE,
)
_FIREWALL_VENDOR_RE = re.compile(
    r"(fortinet|palo.?alto|checkpoint|sophos|watchguard|sonicwall|barracuda)",
    re.IGNORECASE,
)
_VM_VENDOR_RE = re.compile(
    r"(vmware|virtualbox|hyper.?v|xen|kvm|parallels)",
    re.IGNORECASE,
)

# Windows desktop/workstation OS strings → CLIENT
_WIN_CLIENT_RE = re.compile(
    r"windows\s+(10|11|7|8\.?1?|vista|xp|home|pro|enterprise(?! server)|education)",
    re.IGNORECASE,
)
# Windows Server OS strings → SERVER
_WIN_SERVER_RE = re.compile(
    r"windows\s+server",
    re.IGNORECASE,
)
# Linux desktop distros → CLIENT if device looks like a workstation
_LINUX_DESKTOP_RE = re.compile(
    r"(ubuntu\s+desktop|linux\s+mint|pop.?os|fedora\s+workstation|manjaro|zorin|elementary)",
    re.IGNORECASE,
)
# Linux server / headless → SERVER
_LINUX_SERVER_RE = re.compile(
    r"(ubuntu\s+server|debian|centos|rhel|red\s+hat|rocky|alma|suse|opensuse|arch\s+linux|gentoo)",
    re.IGNORECASE,
)
_CISCO_IOS_RE = re.compile(r"(cisco|ios|junos|aruba\s+os|procurve|extremeos)", re.IGNORECASE)


def classify(open_ports: list[int], hostname: str, vendor: str = "") -> str:
    """Return the i-doit object-type constant that best fits this device.

    Called immediately after the port scan before deep-scan data is available.

    Args:
        open_ports: TCP ports found open on the host.
        hostname:   Resolved hostname (may be empty).
        vendor:     MAC OUI vendor string (may be empty).
    """
    from data.models import DeviceType

    ports = set(open_ports)

    # ── Printer ──────────────────────────────────────────────────────────
    if PORT_PRINTER in ports:
        return DeviceType.PRINTER.value
    if vendor and _PRINTER_VENDOR_RE.search(vendor):
        return DeviceType.PRINTER.value

    # ── Firewall / security appliance ────────────────────────────────────
    if vendor and _FIREWALL_VENDOR_RE.search(vendor):
        return DeviceType.ROUTER.value

    # ── Network switch / AP ──────────────────────────────────────────────
    if PORT_SNMP in ports and PORT_WMI not in ports and PORT_RDP not in ports:
        return DeviceType.SWITCH.value
    if vendor and _SWITCH_VENDOR_RE.search(vendor) and PORT_WMI not in ports:
        return DeviceType.SWITCH.value

    # ── Windows host ─────────────────────────────────────────────────────
    if PORT_WMI in ports or PORT_RDP in ports or PORT_SMB in ports:
        if _SERVER_HOST_RE.search(hostname or ""):
            return DeviceType.SERVER.value
        return DeviceType.CLIENT.value   # Windows without server hostname → Client

    # ── Linux / Unix (SSH) ───────────────────────────────────────────────
    if PORT_SSH in ports:
        if _SERVER_HOST_RE.search(hostname or ""):
            return DeviceType.SERVER.value
        return DeviceType.SERVER.value   # default: SSH-only hosts are usually servers

    return DeviceType.UNKNOWN.value


def reclassify_from_scan(device) -> None:  # device: Device
    """Refine device type after deep-scan data (OS, hostname) is available.

    Called by the scanner after WMI / SSH data has been applied to the device.
    Overwrites the port-based classification when the OS string gives clearer
    information.

    Args:
        device: Device instance (modified in place).
    """
    from data.models import DeviceType

    os_str   = (device.os or "").strip()
    hostname = (device.hostname or "").strip()

    if not os_str:
        return  # no OS info → keep port-based classification

    # ── Windows workstation → CLIENT ─────────────────────────────────────
    if _WIN_CLIENT_RE.search(os_str):
        logger.debug(
            "reclassify %s: CLIENT (Windows desktop OS: %s)", device.ip, os_str
        )
        device.device_type = DeviceType.CLIENT.value
        return

    # ── Windows Server → SERVER ───────────────────────────────────────────
    if _WIN_SERVER_RE.search(os_str):
        logger.debug(
            "reclassify %s: SERVER (Windows Server OS: %s)", device.ip, os_str
        )
        device.device_type = DeviceType.SERVER.value
        return

    # ── Cisco / network OS → SWITCH ──────────────────────────────────────
    if _CISCO_IOS_RE.search(os_str) and device.device_type not in (
        DeviceType.PRINTER.value, DeviceType.ROUTER.value
    ):
        logger.debug(
            "reclassify %s: SWITCH (network OS: %s)", device.ip, os_str
        )
        device.device_type = DeviceType.SWITCH.value
        return

    # ── Linux desktop → CLIENT ───────────────────────────────────────────
    if _LINUX_DESKTOP_RE.search(os_str):
        logger.debug(
            "reclassify %s: CLIENT (Linux desktop: %s)", device.ip, os_str
        )
        device.device_type = DeviceType.CLIENT.value
        return

    # ── Linux server → SERVER ────────────────────────────────────────────
    if _LINUX_SERVER_RE.search(os_str):
        logger.debug(
            "reclassify %s: SERVER (Linux server distro: %s)", device.ip, os_str
        )
        device.device_type = DeviceType.SERVER.value
        return

    logger.debug(
        "reclassify %s: no change (unrecognised OS: %s)", device.ip, os_str
    )
