"""Host discovery via concurrent ICMP ping and Windows ARP cache.

Replaces the previous Scapy/Npcap approach.  No external drivers or binaries
required – only standard library (subprocess, ipaddress, concurrent.futures).
"""
from __future__ import annotations
import ipaddress
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

MOCK_HOSTS: list[dict[str, str]] = [
    {"ip": "192.168.1.1",  "mac": "aa:bb:cc:dd:ee:01"},
    {"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:02"},
    {"ip": "192.168.1.20", "mac": "aa:bb:cc:dd:ee:03"},
    {"ip": "192.168.1.30", "mac": "aa:bb:cc:dd:ee:04"},
    {"ip": "192.168.1.40", "mac": "aa:bb:cc:dd:ee:05"},
]

_MAC_RE = re.compile(
    r'([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}'
    r'[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})'
)

_MAX_WORKERS = 100


def sweep(ip_range: str, timeout: int = 2) -> list[dict[str, str]]:
    """Discover live hosts in *ip_range* (CIDR) and return {ip, mac} list.

    Uses concurrent ICMP ping to find responsive hosts, then reads their MAC
    addresses from the Windows ARP cache.
    """
    try:
        network = ipaddress.ip_network(ip_range, strict=False)
    except ValueError:
        logger.error("Invalid IP range: %s", ip_range)
        return []

    hosts = [str(ip) for ip in network.hosts()]
    timeout_ms = max(500, timeout * 1000)
    logger.info(
        "Starting ping sweep of %s (%d hosts, timeout=%dms)",
        ip_range, len(hosts), timeout_ms,
    )

    alive: list[str] = []
    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(hosts))) as pool:
        futures = {pool.submit(_ping, ip, timeout_ms): ip for ip in hosts}
        for future in as_completed(futures):
            if future.result():
                alive.append(futures[future])

    results = [{"ip": ip, "mac": _get_mac(ip)} for ip in alive]
    logger.info("Ping sweep found %d host(s)", len(results))
    return results


def sweep_mock() -> list[dict[str, str]]:
    """Return a fixed list of mock hosts for offline development and testing."""
    logger.info("Using mock sweep data (%d hosts)", len(MOCK_HOSTS))
    return MOCK_HOSTS


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _ping(ip: str, timeout_ms: int) -> bool:
    """Return True if *ip* responds to a single ICMP echo request."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout_ms), ip],
            capture_output=True,
            timeout=timeout_ms / 1000 + 3,
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_mac(ip: str) -> str:
    """Read the MAC address for *ip* from the Windows ARP cache."""
    try:
        result = subprocess.run(
            ["arp", "-a", ip],
            capture_output=True,
            text=True,
            timeout=3,
        )
        match = _MAC_RE.search(result.stdout)
        if match:
            return match.group(0).replace("-", ":").lower()
    except Exception:
        pass
    return "unknown"
