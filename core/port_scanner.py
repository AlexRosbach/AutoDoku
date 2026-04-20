"""Pure Python TCP port scanner – no external binary required.

Replaces the previous python-nmap wrapper.  Uses concurrent socket connect
attempts, which works without Npcap or administrator privileges.
"""
from __future__ import annotations
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

DEFAULT_PORTS: list[int] = [22, 80, 135, 161, 443, 3389, 9100]
CONNECT_TIMEOUT = 0.5  # seconds per port probe


def scan_ports(ip: str, ports: list[int] | None = None) -> list[int]:
    """Return the subset of *ports* that have an open TCP listener on *ip*.

    Args:
        ip:    Target IP address as string.
        ports: Port numbers to probe; defaults to DEFAULT_PORTS.

    Returns:
        Sorted list of port numbers found open.
    """
    target_ports = ports or DEFAULT_PORTS
    open_ports: list[int] = []

    with ThreadPoolExecutor(max_workers=len(target_ports)) as pool:
        futures = {pool.submit(_check_port, ip, p): p for p in target_ports}
        for future in as_completed(futures):
            port = futures[future]
            try:
                if future.result():
                    open_ports.append(port)
            except Exception as exc:
                logger.debug("Port check error %s:%d: %s", ip, port, exc)

    open_ports.sort()
    logger.debug("Port scan %s: open ports %s", ip, open_ports)
    return open_ports


def _check_port(ip: str, port: int) -> bool:
    """Return True if a TCP connection to *ip*:*port* succeeds."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(CONNECT_TIMEOUT)
        return s.connect_ex((ip, port)) == 0
