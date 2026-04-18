"""ARP-based host discovery using scapy.

Broadcasts ARP requests over the given IP range and collects replies.
Requires Npcap (Windows) or libpcap (Linux/macOS) and administrator/root
privileges.  When scapy is unavailable the module degrades gracefully and
returns an empty list (or mock data in mock mode).
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

try:
    from scapy.layers.l2 import ARP, Ether
    from scapy.sendrecv import srp

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logger.warning("scapy is not available – ARP sweep will be skipped")

# Hard-coded mock hosts for offline / non-Windows development
MOCK_HOSTS: list[dict[str, str]] = [
    {"ip": "192.168.1.1",  "mac": "aa:bb:cc:dd:ee:01"},
    {"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:02"},
    {"ip": "192.168.1.20", "mac": "aa:bb:cc:dd:ee:03"},
    {"ip": "192.168.1.30", "mac": "aa:bb:cc:dd:ee:04"},
    {"ip": "192.168.1.40", "mac": "aa:bb:cc:dd:ee:05"},
]

DEFAULT_TIMEOUT = 2
VERBOSE = 0


def sweep(ip_range: str, timeout: int = DEFAULT_TIMEOUT) -> list[dict[str, str]]:
    """Send ARP requests to all hosts in *ip_range* and return responders.

    Args:
        ip_range: CIDR notation, e.g. ``"192.168.1.0/24"``.
        timeout:  Seconds to wait for replies.

    Returns:
        List of dicts with keys ``"ip"`` and ``"mac"``.
    """
    if not SCAPY_AVAILABLE:
        logger.error("scapy not installed – cannot perform ARP sweep")
        return []

    logger.info("Starting ARP sweep of %s (timeout=%ds)", ip_range, timeout)
    packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_range)
    try:
        answered, _ = srp(packet, timeout=timeout, verbose=VERBOSE)
    except Exception as exc:
        logger.error("ARP sweep failed: %s", exc)
        return []

    results = [{"ip": recv.psrc, "mac": recv.hwsrc} for _, recv in answered]
    logger.info("ARP sweep found %d host(s)", len(results))
    return results


def sweep_mock() -> list[dict[str, str]]:
    """Return a fixed list of mock hosts for offline development and testing."""
    logger.info("Using mock ARP sweep data (%d hosts)", len(MOCK_HOSTS))
    return MOCK_HOSTS
