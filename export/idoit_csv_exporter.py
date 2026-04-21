"""i-doit compatible CSV exporter.

Produces a semicolon-separated UTF-8 CSV file that can be imported directly
via *Extras → Import → CSV-Import* in i-doit.

Peripherals are exported as separate rows immediately after their parent device,
using the object type inferred from the peripheral type (Monitor → C__OBJTYPE__MONITOR,
all others → C__OBJTYPE__CABLE or a generic label that i-doit can classify).
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from data.models import Device, Peripheral, ScanSession
from data.session_store import SessionStore

logger = logging.getLogger(__name__)

CSV_SEPARATOR = ";"
CSV_ENCODING  = "utf-8-sig"   # BOM prefix → Excel opens correctly without encoding issues

# Column headers as expected by i-doit's CSV import.
# "Sysid" is placed FIRST: when populated, i-doit uses it as the lookup key
# to UPDATE an existing CMDB object instead of creating a new one.
IDOIT_COLUMNS: list[str] = [
    "Sysid",          # i-doit internal ID – empty = create new; filled = update
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

# Map peripheral types to i-doit object type constants where applicable
_PERIPHERAL_OBJTYPE: dict[str, str] = {
    "Monitor":          "C__OBJTYPE__MONITOR",
    "Drucker (lokal)":  "C__OBJTYPE__PRINTER",
    "Telefon / VoIP":   "C__OBJTYPE__VOIP_PHONE",
}


def export(
    session: ScanSession,
    filepath: str,
    store: SessionStore | None = None,
) -> int:
    """Write *session* devices (and their peripherals) to a CSV file.

    Args:
        session:  The scan session whose devices to export.
        filepath: Destination file path (will be created or overwritten).
        store:    Optional SessionStore; required to load peripheral records.
                  If None, peripherals are not included in the export.

    Returns:
        Number of data rows written (excluding the header row).
    """
    path = Path(filepath)
    rows: list[list[str]] = [IDOIT_COLUMNS]

    for device in session.devices:
        rows.append(_device_to_row(device))

        if store is not None:
            for periph in store.load_peripherals_for_device(device.id):
                rows.append(_peripheral_to_row(periph, device))

    data_rows = len(rows) - 1  # exclude header

    with path.open("w", newline="", encoding=CSV_ENCODING) as fh:
        writer = csv.writer(fh, delimiter=CSV_SEPARATOR, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)

    logger.info("Exported %d row(s) (+header) to %s", data_rows, filepath)
    return data_rows


def _device_to_row(device: Device) -> list[str]:
    """Convert a Device dataclass instance to a CSV row."""
    return [
        device.sysid or "",          # Sysid – update key for i-doit import
        device.device_type or "",
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
    """Convert a Peripheral dataclass instance to a CSV row.

    Inherits Standort/Raum from parent device for location context.
    """
    obj_type = _PERIPHERAL_OBJTYPE.get(periph.peripheral_type, "C__OBJTYPE__OBJECT")
    label = " ".join(filter(None, [periph.manufacturer, periph.model])) or periph.peripheral_type
    return [
        "",   # Sysid – peripherals are always new objects
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
        parent.location or "",   # inherit from parent
        parent.room or "",       # inherit from parent
        parent.department or "", # inherit from parent
        parent.contact or "",    # inherit from parent
        "",   # Inventarnummer
        "",   # CMDB-Status
        periph.notes or "",
    ]
