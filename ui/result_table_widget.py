"""Result table widget showing discovered network devices."""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from data.models import Device, DeviceType

logger = logging.getLogger(__name__)

_COLUMNS: list[tuple[str, str | None]] = [
    ("IP-Adresse",     "ip"),
    ("MAC-Adresse",    "mac"),
    ("Vendor",         "manufacturer"),
    ("Hostname",       "hostname"),
    ("Typ",            "device_type"),
    ("Betriebssystem", "os"),
    ("Status",         "scan_status"),
]

_TYPE_LABELS: dict[str, str] = {
    DeviceType.CLIENT.value:  "Client",
    DeviceType.SERVER.value:  "Server",
    DeviceType.PRINTER.value: "Drucker",
    DeviceType.SWITCH.value:  "Switch",
    DeviceType.ROUTER.value:  "Router",
    DeviceType.UNKNOWN.value: "Unbekannt",
}

_STATUS_LABELS: dict[str, str] = {
    "pending":  "Ausstehend",
    "scanning": "Scannt…",
    "done":     "Fertig",
    "failed":   "Fehler",
}


class ResultTableWidget(QTableWidget):
    """Read-only table with one Device per row.

    Emits :attr:`device_edit_requested` on double-click.
    """

    device_edit_requested = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(_COLUMNS), parent)
        self._devices: list[Device] = []
        self._setup_table()

    def _setup_table(self) -> None:
        self.setHorizontalHeaderLabels([c[0] for c in _COLUMNS])
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)

        hdr = self.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Hostname
        for col in (0, 1, 2, 4, 5, 6):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.setSortingEnabled(True)
        self.cellDoubleClicked.connect(self._on_double_click)

    def add_device(self, device: Device) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self._devices.append(device)
        self._populate_row(row, device)
        self.scrollToBottom()

    def update_device(self, device: Device) -> None:
        for row, d in enumerate(self._devices):
            if d.id == device.id:
                self._devices[row] = device
                self._populate_row(row, device)
                return

    def clear_devices(self) -> None:
        self.setRowCount(0)
        self._devices.clear()

    def get_devices(self) -> list[Device]:
        return list(self._devices)

    def _populate_row(self, row: int, device: Device) -> None:
        for col, (_, attr) in enumerate(_COLUMNS):
            if attr == "device_type":
                text = _TYPE_LABELS.get(device.device_type, device.device_type)
            elif attr == "scan_status":
                text = _STATUS_LABELS.get(device.scan_status, device.scan_status)
            elif attr is not None:
                text = str(getattr(device, attr, "") or "")
            else:
                text = ""

            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, col, item)

    def _on_double_click(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._devices):
            self.device_edit_requested.emit(self._devices[row])
