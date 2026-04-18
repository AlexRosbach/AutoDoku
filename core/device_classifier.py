"""Port-based device type classifier.

Classifies network devices into i-doit object types by inspecting which TCP
ports are open and, secondarily, patterns in the hostname.
"""
from __future__ import annotations
import logging
import re

logger = logging.getLogger(__name__)

# Well-known port numbers used for classification
PORT_SSH = 22
PORT_WMI = 135
PORT_SMB = 445
PORT_SNMP = 161
PORT_RDP = 3389
PORT_PRINTER = 9100

# Hostname patterns that strongly suggest a Windows Server role
_SERVER_HOSTNAME_RE = re.compile(r"(srv|server|dc|ad|nas|esxi|vcenter)", re.IGNORECASE)


def classify(open_ports: list[int], hostname: str) -> str:
    """Return the i-doit object-type constant that best fits this device.

    Args:
        open_ports: List of TCP ports found open on the host.
        hostname:   Resolved hostname (may be empty string).

    Returns:
        One of the DeviceType string values (i-doit object-type constant).
    """
    from data.models import DeviceType

    ports = set(open_ports)

    if PORT_PRINTER in ports:
        logger.debug("classify: PRINTER (port 9100 open)")
        return DeviceType.PRINTER.value

    # SNMP without any Windows management ports → network device / switch
    if PORT_SNMP in ports and PORT_WMI not in ports and PORT_RDP not in ports:
        logger.debug("classify: SWITCH (SNMP only)")
        return DeviceType.SWITCH.value

    # Windows management ports present
    if PORT_WMI in ports or PORT_RDP in ports or PORT_SMB in ports:
        if _SERVER_HOSTNAME_RE.search(hostname):
            logger.debug("classify: SERVER (Windows ports + server hostname)")
            return DeviceType.SERVER.value
        logger.debug("classify: CLIENT (Windows ports)")
        return DeviceType.CLIENT.value

    # SSH only without Windows ports → Linux/Unix, assume server role
    if PORT_SSH in ports:
        logger.debug("classify: SERVER (SSH only)")
        return DeviceType.SERVER.value

    logger.debug("classify: UNKNOWN (no identifying ports)")
    return DeviceType.UNKNOWN.value
