"""Data model definitions for AutoDoku.

Device  – a discovered network device (client, server, switch, printer, …)
Peripheral – any device attached to a Client (monitor, keyboard, mouse, …)
ScanSession – groups all Device records from one scan run.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


class ScanStatus(str, Enum):
    PENDING  = "pending"
    SCANNING = "scanning"
    DONE     = "done"
    FAILED   = "failed"


class DeviceType(str, Enum):
    """i-doit object-type constants."""
    CLIENT  = "C__OBJTYPE__CLIENT"
    SERVER  = "C__OBJTYPE__SERVER"
    PRINTER = "C__OBJTYPE__PRINTER"
    SWITCH  = "C__OBJTYPE__SWITCH"
    ROUTER  = "C__OBJTYPE__ROUTER"
    UNKNOWN = "C__OBJTYPE__DEVICE"
    MONITOR = "C__OBJTYPE__MONITOR"


DEVICE_TYPE_LABELS: dict[str, str] = {
    DeviceType.CLIENT.value:  "Client",
    DeviceType.SERVER.value:  "Server",
    DeviceType.PRINTER.value: "Drucker",
    DeviceType.SWITCH.value:  "Switch",
    DeviceType.ROUTER.value:  "Router",
    DeviceType.UNKNOWN.value: "Unbekannt",
}

DEVICE_TYPE_FROM_LABEL: dict[str, str] = {v: k for k, v in DEVICE_TYPE_LABELS.items()}

CMDB_STATUSES: list[str] = [
    "In Betrieb",
    "Außer Betrieb",
    "Lagernd",
    "Planung",
    "Defekt",
    "Verschrottet",
]

PERIPHERAL_TYPES: list[str] = [
    "Monitor",
    "Tastatur",
    "Maus",
    "Headset",
    "Docking Station",
    "Telefon / VoIP",
    "Drucker (lokal)",
    "USB-Hub",
    "Webcam",
    "Sonstiges",
]


@dataclass
class Device:
    """A single network device discovered during a scan session."""

    id:           str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id:   str = ""
    # ── Network identity (from scan) ──────────────────────────────────
    ip:           str = ""
    mac:          str = ""
    hostname:     str = ""
    # ── Hardware (from WMI / SSH scan) ───────────────────────────────
    device_type:  str = DeviceType.UNKNOWN.value
    os:           str = ""
    manufacturer: str = ""
    model:        str = ""
    serial:       str = ""
    ram_gb:       int | None = None
    cpu:          str = ""
    # ── i-doit documentation fields ───────────────────────────────────
    cmdb_status:  str = ""          # "In Betrieb", "Lagernd", …
    location:     str = ""          # Standort / Gebäude
    room:         str = ""          # Raum
    department:   str = ""          # Abteilung
    contact:      str = ""          # Ansprechpartner
    inventory_no: str = ""          # Inventarnummer
    notes:        str = ""
    # ── Internal ──────────────────────────────────────────────────────
    scan_status:  str = ScanStatus.PENDING.value
    raw_data:     str = ""


@dataclass
class Peripheral:
    """A peripheral device attached to a Client (monitor, keyboard, …)."""

    id:              str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id:       str = ""
    peripheral_type: str = "Monitor"
    manufacturer:    str = ""
    model:           str = ""
    serial:          str = ""
    notes:           str = ""


@dataclass
class ScanSession:
    id:         str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = ""
    ip_range:   str = ""
    name:       str = ""
    devices:    list[Device] = field(default_factory=list)
