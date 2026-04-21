"""Proactive field-suggestion engine for IT documentation.

Generates educated guesses for empty Device fields based on device type,
vendor, hostname patterns and other scan data.  All suggestions are clearly
marked so users can confirm or overwrite them.
"""
from __future__ import annotations

import re
from data.models import Device, DeviceType

_SERVER_VENDOR_RE = re.compile(
    r"(hp|hewlett|dell|fujitsu|lenovo|ibm|supermicro|cisco ucs)", re.IGNORECASE
)
_CLIENT_VENDOR_RE = re.compile(
    r"(dell|hp|lenovo|apple|microsoft|asus|acer|msi)", re.IGNORECASE
)
_SWITCH_VENDOR_RE = re.compile(
    r"(cisco|juniper|aruba|ubiquiti|netgear|tp.?link|mikrotik)", re.IGNORECASE
)
_PRINTER_VENDOR_RE = re.compile(
    r"(kyocera|ricoh|canon|xerox|brother|konica|lexmark|epson|hp)", re.IGNORECASE
)
_GATEWAY_HOST_RE  = re.compile(r"(router|gateway|gw|fritzbox|draytek)", re.IGNORECASE)
_SERVER_HOST_RE   = re.compile(r"(srv|server|dc|nas|esxi|vcenter|exchange|mail)", re.IGNORECASE)
_CLIENT_HOST_RE   = re.compile(r"(pc|laptop|notebook|desktop|ws|workstation)", re.IGNORECASE)

_WIN_VENDOR_RE    = re.compile(r"(dell|hp|lenovo|acer|asus|microsoft|samsung)", re.IGNORECASE)
_CISCO_RE         = re.compile(r"cisco", re.IGNORECASE)


def suggest(device: Device) -> dict[str, str]:
    """Return a dict of field → suggested value for empty fields on *device*.

    Only fields that are currently empty receive suggestions.
    The caller is responsible for rendering suggestions visually (e.g. yellow).
    """
    hints: dict[str, str] = {}
    dtype   = device.device_type
    vendor  = device.manufacturer or ""
    host    = device.hostname     or ""
    os_str  = device.os           or ""

    # ── CMDB-Status ────────────────────────────────────────────────────
    if not device.cmdb_status:
        hints["cmdb_status"] = "In Betrieb"

    # ── Standort ───────────────────────────────────────────────────────
    if not device.location:
        if dtype in (DeviceType.SERVER.value, DeviceType.SWITCH.value, DeviceType.ROUTER.value):
            hints["location"] = "Serverraum"
        elif dtype == DeviceType.CLIENT.value:
            hints["location"] = "Büro"
        elif dtype == DeviceType.PRINTER.value:
            hints["location"] = "Büro / Flur"

    # ── Raum ──────────────────────────────────────────────────────────
    if not device.room:
        if dtype in (DeviceType.SERVER.value, DeviceType.SWITCH.value, DeviceType.ROUTER.value):
            hints["room"] = "EDV-Raum"

    # ── Abteilung ─────────────────────────────────────────────────────
    if not device.department:
        if dtype in (DeviceType.SERVER.value, DeviceType.SWITCH.value, DeviceType.ROUTER.value):
            hints["department"] = "IT"

    # ── Ansprechpartner ───────────────────────────────────────────────
    if not device.contact:
        hints["contact"] = "IT-Administration"

    # ── Betriebssystem ────────────────────────────────────────────────
    if not device.os:
        if dtype == DeviceType.CLIENT.value and _WIN_VENDOR_RE.search(vendor):
            hints["os"] = "Windows 11 Pro"
        elif dtype == DeviceType.SERVER.value and _SERVER_VENDOR_RE.search(vendor):
            hints["os"] = "Windows Server 2022"
        elif dtype == DeviceType.SWITCH.value and _CISCO_RE.search(vendor):
            hints["os"] = "Cisco IOS"

    # ── Hersteller / Modell ───────────────────────────────────────────
    if not device.manufacturer:
        if dtype == DeviceType.SWITCH.value and not vendor:
            hints["manufacturer"] = "Cisco"   # most common in enterprise

    # ── Hostname-Vorschlag wenn leer ──────────────────────────────────
    if not device.hostname and device.ip:
        last = device.ip.rsplit(".", 1)[-1]
        prefix = {
            DeviceType.CLIENT.value:  "PC",
            DeviceType.SERVER.value:  "SRV",
            DeviceType.SWITCH.value:  "SW",
            DeviceType.ROUTER.value:  "GW",
            DeviceType.PRINTER.value: "PRN",
        }.get(dtype, "DEV")
        hints["hostname"] = f"{prefix}-{last.zfill(3)}"

    return hints


def completion_score(device: Device) -> tuple[int, int]:
    """Return (filled_count, total_count) of key documentation fields."""
    fields = [
        device.hostname, device.device_type, device.os, device.manufacturer,
        device.model, device.serial, device.location, device.room,
        device.department, device.contact, device.cmdb_status,
    ]
    filled = sum(1 for f in fields if f and f not in ("C__OBJTYPE__DEVICE",))
    return filled, len(fields)
