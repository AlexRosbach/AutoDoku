"""Port- and vendor-based device type classifier.

Classifies network devices into i-doit object types by inspecting open TCP
ports, the MAC vendor string, and hostname patterns.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

PORT_SSH    = 22
PORT_WMI    = 135
PORT_SMB    = 445
PORT_SNMP   = 161
PORT_RDP    = 3389
PORT_PRINTER = 9100
PORT_HTTP   = 80
PORT_HTTPS  = 443

_SERVER_HOST_RE = re.compile(
    r"(srv|server|dc|ad|nas|esxi|vcenter|pdc|bdc|exchange|mail)", re.IGNORECASE
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
    r"(fortinet|palo alto|checkpoint|sophos|watchguard|sonicwall|barracuda)",
    re.IGNORECASE,
)
_VM_VENDOR_RE = re.compile(
    r"(vmware|virtualbox|hyper.?v|xen|kvm|parallels)", re.IGNORECASE
)


def classify(open_ports: list[int], hostname: str, vendor: str = "") -> str:
    """Return the i-doit object-type constant that best fits this device.

    Args:
        open_ports: TCP ports found open on the host.
        hostname:   Resolved hostname (may be empty).
        vendor:     MAC OUI vendor string (may be empty).

    Returns:
        One of the DeviceType string values (i-doit object-type constant).
    """
    from data.models import DeviceType

    ports = set(open_ports)

    # ── Printer ─────────────────────────────────────────────────────────
    if PORT_PRINTER in ports:
        logger.debug("classify: PRINTER (port 9100)")
        return DeviceType.PRINTER.value
    if vendor and _PRINTER_VENDOR_RE.search(vendor):
        logger.debug("classify: PRINTER (vendor=%s)", vendor)
        return DeviceType.PRINTER.value

    # ── Firewall / security appliance ───────────────────────────────────
    if vendor and _FIREWALL_VENDOR_RE.search(vendor):
        logger.debug("classify: ROUTER (firewall vendor=%s)", vendor)
        return DeviceType.ROUTER.value

    # ── Network switch / AP ─────────────────────────────────────────────
    if PORT_SNMP in ports and PORT_WMI not in ports and PORT_RDP not in ports:
        logger.debug("classify: SWITCH (SNMP, no Windows ports)")
        return DeviceType.SWITCH.value
    if vendor and _SWITCH_VENDOR_RE.search(vendor) and PORT_WMI not in ports:
        logger.debug("classify: SWITCH (switch vendor=%s)", vendor)
        return DeviceType.SWITCH.value

    # ── Virtual machine ─────────────────────────────────────────────────
    if vendor and _VM_VENDOR_RE.search(vendor):
        if _SERVER_HOST_RE.search(hostname):
            logger.debug("classify: SERVER (VM, server hostname)")
            return DeviceType.SERVER.value
        # VM → classify further by ports, fall through

    # ── Windows host ────────────────────────────────────────────────────
    if PORT_WMI in ports or PORT_RDP in ports or PORT_SMB in ports:
        if _SERVER_HOST_RE.search(hostname):
            logger.debug("classify: SERVER (Windows + server hostname)")
            return DeviceType.SERVER.value
        logger.debug("classify: CLIENT (Windows ports)")
        return DeviceType.CLIENT.value

    # ── Linux / Unix ────────────────────────────────────────────────────
    if PORT_SSH in ports:
        if _SERVER_HOST_RE.search(hostname):
            logger.debug("classify: SERVER (SSH + server hostname)")
            return DeviceType.SERVER.value
        logger.debug("classify: SERVER (SSH only, assume server)")
        return DeviceType.SERVER.value

    logger.debug("classify: UNKNOWN (no identifying ports/vendor)")
    return DeviceType.UNKNOWN.value
