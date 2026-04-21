"""Data model definitions for AutoDoku.

Provides dataclasses for Device, Monitor and ScanSession as well as the
ScanStatus string-enum used throughout the application.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum


class ScanStatus(str, Enum):
    """Lifecycle states for a single device scan."""

    PENDING = "pending"
    SCANNING = "scanning"
    DONE = "done"
    FAILED = "failed"


class DeviceType(str, Enum):
    """i-doit object-type constants used as device classification values."""

    CLIENT  = "C__OBJTYPE__CLIENT"
    SERVER  = "C__OBJTYPE__SERVER"
    PRINTER = "C__OBJTYPE__PRINTER"
    SWITCH  = "C__OBJTYPE__SWITCH"
    ROUTER  = "C__OBJTYPE__ROUTER"
    UNKNOWN = "C__OBJTYPE__DEVICE"
    MONITOR = "C__OBJTYPE__MONITOR"


@dataclass
class Device:
    """Represents a single network device discovered during a scan session."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    ip: str = ""
    mac: str = ""
    hostname: str = ""
    device_type: str = DeviceType.UNKNOWN.value
    os: str = ""
    manufacturer: str = ""
    model: str = ""
    serial: str = ""
    ram_gb: int | None = None
    cpu: str = ""
    location: str = ""
    department: str = ""
    notes: str = ""
    scan_status: str = ScanStatus.PENDING.value
    raw_data: str = ""


@dataclass
class Monitor:
    """Represents a monitor attached to a CLIENT-type device."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = ""
    manufacturer: str = ""
    model: str = ""
    serial: str = ""
    notes: str = ""


@dataclass
class ScanSession:
    """Groups a set of devices discovered during one scan run."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = ""
    ip_range: str = ""
    name: str = ""
    devices: list[Device] = field(default_factory=list)
