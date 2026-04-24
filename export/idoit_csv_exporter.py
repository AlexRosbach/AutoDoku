"""i-doit compatible CSV exporter.

Produces a semicolon-separated UTF-8-sig CSV file that can be imported directly
via *Extras → Import → CSV-Import* in i-doit.

Peripherals are exported as separate rows immediately after their parent device,
using the human-readable object-type labels that i-doit expects (e.g. "Client",
"Server", "Monitor").  Auto-suggested peripherals (is_suggestion=True) that the
user never filled in (no model AND no serial) are silently skipped.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from data.models import (
    DEVICE_TYPE_LABELS,
    PERIPHERAL_IDOIT_TYPE,
    Device,
    Peripheral,
    ScanSession,
)

logger = logging.getLogger(__name__)

CSV_SEPARATOR = ";"
CSV_ENCODING  = "utf-8-sig"   # BOM prefix → Excel opens without encoding issues

# Column headers as expected by i-doit's CSV import.
# "Sysid" first: when populated, i-doit uses it as the lookup key to UPDATE an
# existing CMDB object instead of creating a new one.
IDOIT_COLUMNS: list[str] = [
    "Sysid",
    "Objekt-Typ",
    "Bezeichnung",
    "IP-Adresse",
    "MAC-Adresse",
    "Hostname",
    "Betriebssystem",
    "Hersteller",
    "Modell",
    "Seriennummer",
    "RAM (GB)",
    "CPU",
    "Standort",
    "Raum",
    "Abteilung",
    "Ansprechpartner",
    "Inventarnummer",
    "CMDB-Status",
    "Notizen",
]


def export(session: ScanSession, filepath: str) -> int:
    """Write *session* devices (and their peripherals) to a CSV file.

    Args:
        session:  The scan session whose devices to export.
        filepath: Destination file path (will be created or overwritten).

    Returns:
        Number of data rows written (excluding the header row).
    """
    path = Path(filepath)
    rows: list[list[str]] = [IDOIT_COLUMNS]

    for device in session.devices:
        rows.append(_device_to_row(device))

        for periph in device.peripherals:
            # Skip empty auto-suggestions the user never touched
            if periph.is_suggestion and not periph.model and not periph.serial:
                continue
            rows.append(_peripheral_to_row(periph, device))

    data_rows = len(rows) - 1  # exclude header

    with path.open("w", newline="", encoding=CSV_ENCODING) as fh:
        writer = csv.writer(fh, delimiter=CSV_SEPARATOR, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)

    logger.info("Exported %d row(s) (+header) to %s", data_rows, filepath)
    return data_rows


def _device_to_row(device: Device) -> list[str]:
    """Convert a Device to a CSV row with human-readable Objekt-Typ."""
    obj_type = DEVICE_TYPE_LABELS.get(device.device_type, "Unbekannt")
    return [
        device.sysid or "",
        obj_type,
        device.hostname or device.ip or "",
        device.ip or "",
        device.mac or "",
        device.hostname or "",
        device.os or "",
        device.manufacturer or "",
        device.model or "",
        device.serial or "",
        str(device.ram_gb) if device.ram_gb is not None else "",
        device.cpu or "",
        device.location or "",
        device.room or "",
        device.department or "",
        device.contact or "",
        device.inventory_no or "",
        device.cmdb_status or "",
        device.notes or "",
    ]


def _peripheral_to_row(periph: Peripheral, parent: Device) -> list[str]:
    """Convert a Peripheral to a CSV row.

    Uses the human-readable i-doit label from PERIPHERAL_IDOIT_TYPE where
    available; falls back to the peripheral_type name itself.
    Inherits Standort/Raum from parent device for location context.
    """
    obj_type = PERIPHERAL_IDOIT_TYPE.get(periph.peripheral_type, periph.peripheral_type)
    label = " ".join(filter(None, [periph.manufacturer, periph.model])) or periph.peripheral_type
    return [
        periph.sysid or "",   # Sysid – populated on re-import to update existing object
        obj_type,
        label,
        "",   # IP
        "",   # MAC
        "",   # Hostname
        "",   # OS
        periph.manufacturer or "",
        periph.model or "",
        periph.serial or "",
        "",   # RAM
        "",   # CPU
        parent.location or "",
        parent.room or "",
        parent.department or "",
        parent.contact or "",
        "",   # Inventarnummer
        "",   # CMDB-Status
        periph.notes or "",
    ]
