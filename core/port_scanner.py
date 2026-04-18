"""TCP port scanner wrapping the nmap command-line tool via python-nmap.

Note: the nmap binary must be installed on the target machine and available
on PATH.  It cannot be bundled inside the portable EXE.
"""
from __future__ import annotations
import logging

import nmap

logger = logging.getLogger(__name__)

DEFAULT_PORTS: list[int] = [22, 80, 135, 161, 443, 3389, 9100]


def scan_ports(ip: str, ports: list[int] | None = None) -> list[int]:
    """Scan *ip* for open TCP ports and return the open ones.

    Args:
        ip:    Target IP address as string.
        ports: List of port numbers to probe; defaults to DEFAULT_PORTS.

    Returns:
        List of port numbers found open on the host.
    """
    target_ports = ports or DEFAULT_PORTS
    port_str = ",".join(str(p) for p in target_ports)

    nm = nmap.PortScanner()
    try:
        # -T4 for faster timing, --open to suppress closed/filtered output
        nm.scan(hosts=ip, ports=port_str, arguments="-T4 --open")
    except nmap.PortScannerError as exc:
        logger.error("nmap scan failed for %s: %s", ip, exc)
        return []

    open_ports: list[int] = []
    if ip not in nm.all_hosts():
        return open_ports

    for proto in nm[ip].all_protocols():
        for port, state_info in nm[ip][proto].items():
            if state_info.get("state") == "open":
                open_ports.append(port)

    logger.debug("Port scan %s: open ports %s", ip, open_ports)
    return open_ports
