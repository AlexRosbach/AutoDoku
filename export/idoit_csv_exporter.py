"""i-doit compatible CSV exporter.

Produces a semicolon-separated UTF-8 CSV file that can be imported directly
via *Extras → Import → CSV-Import* in i-doit.

Monitors are exported as separate rows immediately after their parent device
using the object type ``C__OBJTYPE__MONITOR``.
"""
from __future__ import annotations
import csv
import logging
from pathlib import Path

from data.models import Device, Monitor, ScanSession
from data.session_store import SessionStore

logger = logging.getLogger(__name__)

CSV_SEPARATOR = ";"
CSV_ENCODING = "utf-8"

# Column headers as expected by i-doit's CSV import
IDOIT_COLUMNS: list[str] = [
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
    "Abteilung",
    "Notizen",
]


def export(
    session: ScanSession,
    filepath: str,
    store: SessionStore | None = None,
) -> int:
    """Write *session* devices (and their monitors) to a CSV file.

    Args:
        session:  The scan session whose devices to export.
        filepath: Destination file path (will be created or overwritten).
        store:    Optional SessionStore; required to load monitor records.
                  If None, monitors are not included in the export.

    Returns:
        Number of rows written (excluding the header row).
    """
    path = Path(filepath)
    rows: list[list[str]] = [IDOIT_COLUMNS]

    for device in session.devices:
        rows.append(_device_to_row(device))

        if store is not None:
            for monitor in store.load_monitors_for_device(device.id):
                rows.append(_monitor_to_row(monitor))

    data_rows = len(rows) - 1  # exclude header

    with path.open("w", newline="", encoding=CSV_ENCODING) as fh:
        writer = csv.writer(fh, delimiter=CSV_SEPARATOR, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)

    logger.info(
        "Exported %d device row(s) (+header) to %s",
        data_rows,
        filepath,
    )
    return data_rows


def _device_to_row(device: Device) -> list[str]:
    """Convert a Device dataclass instance to a CSV row."""
    return [
        device.device_type,
        device.hostname or device.ip,
        device.ip,
        device.mac,
        device.hostname,
        device.os,
        device.manufacturer,
        device.model,
        device.serial,
        str(device.ram_gb) if device.ram_gb is not None else "",
        device.cpu,
        device.location,
        device.department,
        device.notes,
    ]


def _monitor_to_row(monitor: Monitor) -> list[str]:
    """Convert a Monitor dataclass instance to a CSV row."""
    label = monitor.model or monitor.serial or monitor.manufacturer or "Monitor"
    return [
        "C__OBJTYPE__MONITOR",
        label,
        "",   # IP
        "",   # MAC
        "",   # Hostname
        "",   # OS
        monitor.manufacturer,
        monitor.model,
        monitor.serial,
        "",   # RAM
        "",   # CPU
        "",   # Standort
        "",   # Abteilung
        monitor.notes,
    ]
