"""Pre-export review dialog.

Shows all scanned devices in an editable table so the user can fill empty
fields and make last-minute corrections before the CSV is written.
Suggested values are pre-filled automatically for empty cells.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from data.models import Device, DeviceType

logger = logging.getLogger(__name__)

# Columns shown in the review table: (header, Device attribute, editable)
_COLS: list[tuple[str, str, bool]] = [
    ("IP",           "ip",           False),
    ("MAC",          "mac",          False),
    ("Vendor",       "manufacturer", True),
    ("Hostname",     "hostname",     True),
    ("Typ",          "device_type",  False),
    ("OS",           "os",           True),
    ("Modell",       "model",        True),
    ("Seriennummer", "serial",       True),
    ("Standort",     "location",     True),
    ("Abteilung",    "department",   True),
    ("Notizen",      "notes",        True),
]

_TYPE_LABELS: dict[str, str] = {
    DeviceType.CLIENT.value:  "Client",
    DeviceType.SERVER.value:  "Server",
    DeviceType.PRINTER.value: "Drucker",
    DeviceType.SWITCH.value:  "Switch",
    DeviceType.ROUTER.value:  "Router",
    DeviceType.UNKNOWN.value: "Unbekannt",
}

# Suggested values for common empty fields based on device type
_SUGGESTIONS: dict[str, dict[str, str]] = {
    DeviceType.CLIENT.value:  {"location": "Büro", "department": "IT"},
    DeviceType.SERVER.value:  {"location": "Serverraum", "department": "IT"},
    DeviceType.SWITCH.value:  {"location": "Serverraum / Patchfeld"},
    DeviceType.PRINTER.value: {"location": "Büro"},
    DeviceType.ROUTER.value:  {"location": "Serverraum"},
}


class ExportReviewDialog(QDialog):
    """Modal dialog that lets the user review and edit device data before export.

    Call :meth:`get_devices` after ``exec()`` returns ``Accepted`` to retrieve
    the (possibly modified) device list.
    """

    def __init__(self, devices: list[Device], parent=None) -> None:
        super().__init__(parent)
        self._devices = [_copy_device(d) for d in devices]
        self.setWindowTitle("Export-Vorschau – Daten prüfen und ergänzen")
        self.resize(1100, 600)
        self._build_ui()
        self._populate()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        hint = QLabel(
            "Weiß hinterlegte Felder sind bearbeitbar. "
            "Vorschläge (kursiv) für leere Pflichtfelder wurden automatisch eingefügt – "
            "bitte prüfen und ggf. anpassen."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(hint)

        self._table = QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels([c[0] for c in _COLS])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)

        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(True)
        for i, (_, _, editable) in enumerate(_COLS):
            if editable:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Exportieren")
        buttons.accepted.connect(self._commit_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self) -> None:
        suggestions = _SUGGESTIONS
        for row_idx, device in enumerate(self._devices):
            self._table.insertRow(row_idx)
            dev_suggestions = suggestions.get(device.device_type, {})

            for col_idx, (_, attr, editable) in enumerate(_COLS):
                if attr == "device_type":
                    text = _TYPE_LABELS.get(device.device_type, device.device_type)
                else:
                    text = str(getattr(device, attr, "") or "")

                suggested = False
                if editable and not text and attr in dev_suggestions:
                    text = dev_suggestions[attr]
                    suggested = True

                item = QTableWidgetItem(text)
                if not editable:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setForeground(Qt.GlobalColor.gray)
                elif suggested:
                    # Italic to signal auto-suggestion
                    font = item.font()
                    font.setItalic(True)
                    item.setFont(font)
                    item.setForeground(Qt.GlobalColor.cyan)

                self._table.setItem(row_idx, col_idx, item)

    def _commit_and_accept(self) -> None:
        """Write table edits back into the device copies."""
        for row_idx, device in enumerate(self._devices):
            for col_idx, (_, attr, editable) in enumerate(_COLS):
                if not editable or attr == "device_type":
                    continue
                item = self._table.item(row_idx, col_idx)
                if item:
                    setattr(device, attr, item.text().strip())
        self.accept()

    def get_devices(self) -> list[Device]:
        """Return the (possibly modified) device list."""
        return list(self._devices)


def _copy_device(d: Device) -> Device:
    """Return a shallow copy of *d* for safe in-dialog editing."""
    from dataclasses import replace
    return replace(d)
