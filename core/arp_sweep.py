"""ARP-based host discovery using the Windows SendARP API.

Calls iphlpapi.dll!SendARP via ctypes – no subprocess spawning,
no Npcap/WinPcap driver, no administrator privileges required.
SendARP sends a single ARP broadcast per IP and returns the MAC address
directly, giving us host liveness + MAC address in one call.
"""
from __future__ import annotations

import ctypes
import ipaddress
import logging
import socket
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Windows IPHLPAPI
try:
    _iphlpapi = ctypes.windll.iphlpapi
    _SENDARP_AVAILABLE = True
except (AttributeError, OSError):
    _SENDARP_AVAILABLE = False
    logger.warning("iphlpapi not available – running on non-Windows?")

MOCK_HOSTS: list[dict[str, str]] = [
    {"ip": "192.168.1.1",  "mac": "aa:bb:cc:dd:ee:01"},
    {"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:02"},
    {"ip": "192.168.1.20", "mac": "aa:bb:cc:dd:ee:03"},
    {"ip": "192.168.1.30", "mac": "aa:bb:cc:dd:ee:04"},
    {"ip": "192.168.1.40", "mac": "aa:bb:cc:dd:ee:05"},
]

_MAX_WORKERS = 128


def sweep(ip_range: str, timeout: int = 2) -> list[dict[str, str]]:
    """Discover live hosts in *ip_range* (CIDR) via ARP.

    Returns a list of ``{ip, mac}`` dicts for every host that responds.
    Works on the local broadcast domain (same subnet / VLAN).
    """
    if not _SENDARP_AVAILABLE:
        logger.error("SendARP not available on this platform")
        return []

    try:
        network = ipaddress.ip_network(ip_range, strict=False)
    except ValueError:
        logger.error("Invalid IP range: %s", ip_range)
        return []

    hosts = [str(ip) for ip in network.hosts()]
    logger.info("ARP sweep %s: probing %d addresses", ip_range, len(hosts))

    results: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(hosts))) as pool:
        futures = {pool.submit(_send_arp, ip): ip for ip in hosts}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                mac = future.result()
            except Exception:
                mac = None
            if mac:
                results.append({"ip": ip, "mac": mac})

    logger.info("ARP sweep found %d host(s)", len(results))
    return results


def sweep_mock() -> list[dict[str, str]]:
    """Return a fixed list of mock hosts for offline development and testing."""
    logger.info("Using mock sweep data (%d hosts)", len(MOCK_HOSTS))
    return MOCK_HOSTS


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _send_arp(ip: str) -> str | None:
    """Call SendARP for *ip* and return the MAC address, or None on failure.

    SendARP (iphlpapi.dll) sends an ARP request on the local network and
    blocks until either a reply arrives or the internal timeout expires.
    No raw sockets, no Npcap, no elevated privileges required.
    """
    try:
        # Convert dotted-quad to 32-bit integer in native byte order,
        # which is the format Windows IPAddr (DWORD) expects.
        dest_int = struct.unpack("I", socket.inet_aton(ip))[0]

        mac_buf = (ctypes.c_ubyte * 8)()   # 8 bytes; MAC occupies first 6
        mac_len = ctypes.c_ulong(8)

        ret = _iphlpapi.SendARP(
            dest_int,              # DestIP
            0,                     # SrcIP  (0 = use primary interface)
            mac_buf,               # pMacAddr
            ctypes.byref(mac_len), # PhyAddrLen (in/out)
        )

        if ret == 0 and mac_len.value >= 6:   # ERROR_SUCCESS
            return ":".join(f"{mac_buf[i]:02x}" for i in range(6))
        return None
    except Exception as exc:
        logger.debug("SendARP %s failed: %s", ip, exc)
        return None
