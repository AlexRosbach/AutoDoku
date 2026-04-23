"""Import a previously exported AutoDoku CSV back into memory.

The exported file has this row structure:
  - Header row (column names)
  - One row per Device
  - Peripheral rows immediately following their parent device row
    (identified by Objekt-Typ matching a known peripheral type label)

This module reconstructs a list[Device] from such a file, including
the peripheral objects attached to each device.
"""
from __future__ import annotations

import csv
import logging
import uuid
from pathlib import Path

from data.models import (
    CMDB_STATUSES,
    DEVICE_TYPE_FROM_LABEL,
    DEVICE_TYPE_LABELS,
    PERIPHERAL_IDOIT_TYPE,
    PERIPHERAL_TYPES,
    Device,
    DeviceType,
    Peripheral,
    ScanStatus,
)

logger = logging.getLogger(__name__)

CSV_SEPARATOR = ";"

# All object-type labels that belong to peripheral objects in the CSV
_PERIPHERAL_TYPE_LABELS: set[str] = set(PERIPHERAL_IDOIT_TYPE.values()) | {
    # Also accept the peripheral_type names directly
    t for t in PERIPHERAL_TYPES
}

# Reverse map: i-doit label → peripheral_type string
_LABEL_TO_PERIPH_TYPE: dict[str, str] = {v: k for k, v in PERIPHERAL_IDOIT_TYPE.items()}


def import_csv(filepath: str) -> list[Device]:
    """Parse an AutoDoku-exported CSV and return a list of Device objects.

    Args:
        filepath: Path to the CSV file (UTF-8 or UTF-8-sig).

    Returns:
        List of Device instances with peripherals attached.

    Raises:
        ValueError: If the file cannot be parsed as an AutoDoku CSV.
        OSError:    If the file cannot be opened.
    """
    path = Path(filepath)
    devices: list[Device] = []
    current_device: Device | None = None

    with path.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.DictReader(fh, delimiter=CSV_SEPARATOR)

        if reader.fieldnames is None:
            raise ValueError("CSV-Datei hat keine Kopfzeile.")

        headers = [h.strip() for h in reader.fieldnames]
        logger.info("CSV import: headers = %s", headers)

        for row_num, row in enumerate(reader, start=2):
            obj_type = row.get("Objekt-Typ", "").strip()

            if _is_peripheral_row(obj_type):
                # ── Peripheral row ─────────────────────────────────────
                if current_device is None:
                    logger.warning("Row %d: peripheral without parent device – skipped", row_num)
                    continue
                p = _row_to_peripheral(row, current_device.id)
                current_device.peripherals.append(p)

            else:
                # ── Device row ─────────────────────────────────────────
                device = _row_to_device(row)
                devices.append(device)
                current_device = device

    logger.info("CSV import: loaded %d device(s)", len(devices))
    return devices


# ---------------------------------------------------------------------------
# Row → model helpers
# ---------------------------------------------------------------------------

def _is_peripheral_row(obj_type_label: str) -> bool:
    """Return True if *obj_type_label* identifies a peripheral object."""
    return (
        obj_type_label in _PERIPHERAL_TYPE_LABELS
        or obj_type_label in PERIPHERAL_TYPES
    )


def _row_to_device(row: dict[str, str]) -> Device:
    obj_type_label = row.get("Objekt-Typ", "").strip()
    device_type = DEVICE_TYPE_FROM_LABEL.get(obj_type_label, DeviceType.UNKNOWN.value)

    ram_gb: int | None = None
    try:
        ram_raw = row.get("RAM (GB)", "").strip()
        if ram_raw:
            ram_gb = int(float(ram_raw))
    except (ValueError, TypeError):
        pass

    return Device(
        id=str(uuid.uuid4()),
        sysid=row.get("Sysid", "").strip(),
        device_type=device_type,
        ip=row.get("IP-Adresse", "").strip(),
        mac=row.get("MAC-Adresse", "").strip(),
        hostname=row.get("Hostname", "").strip(),
        os=row.get("Betriebssystem", "").strip(),
        manufacturer=row.get("Hersteller", "").strip(),
        model=row.get("Modell", "").strip(),
        serial=row.get("Seriennummer", "").strip(),
        ram_gb=ram_gb,
        cpu=row.get("CPU", "").strip(),
        location=row.get("Standort", "").strip(),
        room=row.get("Raum", "").strip(),
        department=row.get("Abteilung", "").strip(),
        contact=row.get("Ansprechpartner", "").strip(),
        inventory_no=row.get("Inventarnummer", "").strip(),
        cmdb_status=row.get("CMDB-Status", "").strip(),
        notes=row.get("Notizen", "").strip(),
        scan_status=ScanStatus.DONE.value,
        peripherals=[],
    )


def _row_to_peripheral(row: dict[str, str], device_id: str) -> Peripheral:
    obj_type_label = row.get("Objekt-Typ", "").strip()
    # Map i-doit label back to peripheral_type; fall back to the label itself
    periph_type = _LABEL_TO_PERIPH_TYPE.get(obj_type_label, obj_type_label)
    if periph_type not in PERIPHERAL_TYPES:
        periph_type = "Sonstiges"

    return Peripheral(
        id=str(uuid.uuid4()),
        device_id=device_id,
        peripheral_type=periph_type,
        manufacturer=row.get("Hersteller", "").strip(),
        model=row.get("Modell", "").strip(),
        serial=row.get("Seriennummer", "").strip(),
        notes=row.get("Notizen", "").strip(),
        is_suggestion=False,
    )
