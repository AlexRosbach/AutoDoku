"""MAC address vendor (OUI) lookup.

Uses the ``manuf`` library (Wireshark OUI database, bundled offline) when
available, and falls back to a built-in table of the most common vendors.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_MAC_NORM_RE = re.compile(r"[:\-\.]")

# ---------------------------------------------------------------------------
# manuf backend (optional – works offline, covers ~30 000 OUI prefixes)
# ---------------------------------------------------------------------------
try:
    from manuf import manuf as _manuf_mod
    _parser = _manuf_mod.MacParser()
    _MANUF_AVAILABLE = True
    logger.debug("manuf OUI database loaded")
except Exception:
    _parser = None
    _MANUF_AVAILABLE = False
    logger.debug("manuf not available, using built-in OUI table")


# ---------------------------------------------------------------------------
# Built-in fallback table (covers the most common office/enterprise vendors)
# ---------------------------------------------------------------------------
_BUILTIN: dict[str, str] = {
    # Apple
    "001B63": "Apple", "000D93": "Apple", "001451": "Apple",
    "0016CB": "Apple", "0017F2": "Apple", "001731": "Apple",
    "001E52": "Apple", "001EC2": "Apple", "002241": "Apple",
    "0023DF": "Apple", "0025BC": "Apple", "0026B9": "Apple",
    "0026BB": "Apple", "00264A": "Apple",
    # Dell
    "001517": "Dell", "001A4B": "Dell", "0019B9": "Dell",
    "001E4F": "Dell", "002481": "Dell", "18A995": "Dell",
    "1C40DE": "Dell", "F4E9D4": "Dell", "3417EB": "Dell",
    "BCEE7B": "Dell", "34E6D7": "Dell", "B083FE": "Dell",
    # HP / HPE
    "001060": "HP", "001321": "HP", "001635": "HP",
    "3C4A92": "HP", "9CED84": "HP", "286ED4": "HP",
    "3C52A1": "HP", "001E0B": "HP", "002481": "HP",
    "10604B": "HP", "30E171": "HP", "E8B748": "HP",
    # Lenovo / IBM
    "000C29": "VMware",  # intentionally here for VMs (see below)
    "000D3A": "Microsoft", "001DD8": "Microsoft",
    "005056": "VMware", "000C29": "VMware", "000569": "VMware",
    # Lenovo
    "00236C": "Lenovo", "28D244": "Lenovo", "484D7E": "Lenovo",
    "54EEA8": "Lenovo", "3C970E": "Lenovo",
    # Cisco
    "000142": "Cisco", "001301": "Cisco", "001A2F": "Cisco",
    "001B54": "Cisco", "001C58": "Cisco", "001E14": "Cisco",
    "001E7A": "Cisco", "0021A0": "Cisco", "00221D": "Cisco",
    "002697": "Cisco", "C89C1D": "Cisco", "F866F2": "Cisco",
    "706D15": "Cisco", "3C0754": "Cisco", "CCD869": "Cisco",
    # Juniper
    "0019E2": "Juniper", "001E41": "Juniper", "002481": "Juniper",
    "2C6BF5": "Juniper",
    # Aruba (HPE)
    "001A1E": "Aruba", "24DE C6": "Aruba", "6C5C14": "Aruba",
    "94B4CF": "Aruba", "D8C7C8": "Aruba",
    # Ubiquiti
    "002722": "Ubiquiti", "04180F": "Ubiquiti", "0418D6": "Ubiquiti",
    "44D9E7": "Ubiquiti", "68722D": "Ubiquiti", "788A20": "Ubiquiti",
    "802AA8": "Ubiquiti", "B4FBE4": "Ubiquiti", "DC9FDB": "Ubiquiti",
    "E063DA": "Ubiquiti", "F09FC2": "Ubiquiti", "FC2172": "Ubiquiti",
    # Fortinet
    "000966": "Fortinet", "001309": "Fortinet", "70E8B2": "Fortinet",
    "90BCA9": "Fortinet",
    # Palo Alto
    "B46902": "Palo Alto Networks",
    # Samsung
    "001247": "Samsung", "001632": "Samsung", "0021D2": "Samsung",
    "002339": "Samsung", "002454": "Samsung", "002566": "Samsung",
    "08ECA9": "Samsung", "1077B1": "Samsung",
    # Intel (NIC)
    "001B21": "Intel", "001E65": "Intel", "0022FB": "Intel",
    "0024D7": "Intel", "0026B9": "Intel", "6C3BE5": "Intel",
    "8086F2": "Intel", "A0369F": "Intel",
    # Realtek (NIC)
    "00E04C": "Realtek", "D05099": "Realtek", "04421A": "Realtek",
    # Broadcom
    "000AF7": "Broadcom", "00104B": "Broadcom",
    # Printers
    "000D4B": "Ricoh", "001252": "Ricoh",
    "00012F": "Kyocera", "001CB2": "Kyocera", "A40C66": "Kyocera",
    "001500": "Canon", "0000D0": "Canon", "34C93A": "Canon",
    "001E8F": "Brother", "305A3A": "Brother",
    "001E40": "Xerox",  "000D2D": "Xerox",
    "000B65": "Konica Minolta",
    "000747": "HP Printer",
    # Network gear
    "000AEB": "Netgear", "001B2F": "Netgear", "20E52A": "Netgear",
    "28C68E": "Netgear", "4C60DE": "Netgear", "A040A0": "Netgear",
    "C03F0E": "Netgear", "E091F5": "Netgear",
    "000D0B": "TP-Link", "1C3BF3": "TP-Link", "50C7BF": "TP-Link",
    "60E3270": "TP-Link", "C46E1F": "TP-Link", "D46AA8": "TP-Link",
    "E848B8": "TP-Link", "F81A67": "TP-Link",
    "001D7E": "MikroTik", "2CC8E5": "MikroTik", "4C5E0C": "MikroTik",
    "64D154": "MikroTik", "6C3B6B": "MikroTik", "B8698E": "MikroTik",
    "D4CA6D": "MikroTik", "E48D8C": "MikroTik",
    # Virtualization
    "000C29": "VMware", "005056": "VMware", "000569": "VMware",
    "0003FF": "Microsoft Hyper-V",
    "080027": "VirtualBox",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup(mac: str) -> str:
    """Return the vendor name for *mac*, or an empty string if unknown.

    Accepts any common MAC notation (colons, hyphens, dots, or plain hex).
    """
    if not mac or mac == "unknown":
        return ""

    normalized = _MAC_NORM_RE.sub("", mac).upper()
    if len(normalized) < 6:
        return ""

    if _MANUF_AVAILABLE and _parser is not None:
        try:
            result = _parser.get_manuf(mac)
            if result:
                return result
        except Exception:
            pass

    return _BUILTIN.get(normalized[:6], "")
