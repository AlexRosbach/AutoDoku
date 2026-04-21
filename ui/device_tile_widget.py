"""Kachel-/Card-Ansicht für gefundene Netzwerkgeräte."""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from data.models import Device, DeviceType

logger = logging.getLogger(__name__)

# Unicode icons per device type (no image files needed)
_TYPE_ICONS: dict[str, str] = {
    DeviceType.CLIENT.value:  "🖥",
    DeviceType.SERVER.value:  "🗄",
    DeviceType.PRINTER.value: "🖨",
    DeviceType.SWITCH.value:  "🔀",
    DeviceType.ROUTER.value:  "📡",
    DeviceType.UNKNOWN.value: "❓",
}

_TYPE_LABELS: dict[str, str] = {
    DeviceType.CLIENT.value:  "Client",
    DeviceType.SERVER.value:  "Server",
    DeviceType.PRINTER.value: "Drucker",
    DeviceType.SWITCH.value:  "Switch",
    DeviceType.ROUTER.value:  "Router",
    DeviceType.UNKNOWN.value: "Unbekannt",
}

_TILE_COLS = 4   # cards per row (auto-adjusts via grid)


class _DeviceCard(QFrame):
    """Single device card widget."""

    clicked = pyqtSignal(object)   # Device

    def __init__(self, device: Device, parent=None) -> None:
        super().__init__(parent)
        self._device = device
        self.setObjectName("deviceCard")
        self.setFixedSize(200, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Doppelklick zum Bearbeiten")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        d = self._device
        icon = _TYPE_ICONS.get(d.device_type, "❓")
        type_label = _TYPE_LABELS.get(d.device_type, d.device_type)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon_lbl)

        name = d.hostname or d.ip
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        for text in (
            d.ip,
            d.manufacturer or "",
            type_label,
            d.os[:30] + "…" if len(d.os) > 30 else d.os,
        ):
            if text:
                lbl = QLabel(text)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("color: #aaa; font-size: 11px;")
                layout.addWidget(lbl)

        layout.addStretch()

    def mouseDoubleClickEvent(self, _event) -> None:
        self.clicked.emit(self._device)

    def update_device(self, device: Device) -> None:
        self._device = device
        # Rebuild the card content
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._build()


class DeviceTileWidget(QScrollArea):
    """Scrollable grid of device cards.

    Emits :attr:`device_edit_requested` on double-click of any card.
    """

    device_edit_requested = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._devices: list[Device] = []
        self._cards: list[_DeviceCard] = []

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(12)
        self._grid.setContentsMargins(12, 12, 12, 12)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Dynamic column count based on width
        self._col_count = _TILE_COLS

    def add_device(self, device: Device) -> None:
        card = _DeviceCard(device)
        card.clicked.connect(self.device_edit_requested)

        idx = len(self._cards)
        row, col = divmod(idx, self._col_count)
        self._grid.addWidget(card, row, col)

        self._devices.append(device)
        self._cards.append(card)

    def update_device(self, device: Device) -> None:
        for i, d in enumerate(self._devices):
            if d.id == device.id:
                self._devices[i] = device
                self._cards[i].update_device(device)
                return

    def clear_devices(self) -> None:
        for card in self._cards:
            card.deleteLater()
        self._devices.clear()
        self._cards.clear()

    def get_devices(self) -> list[Device]:
        return list(self._devices)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Recalculate columns based on available width
        available = self.viewport().width() - 24
        new_cols = max(1, available // 212)
        if new_cols != self._col_count:
            self._col_count = new_cols
            self._relayout()

    def _relayout(self) -> None:
        for i, card in enumerate(self._cards):
            row, col = divmod(i, self._col_count)
            self._grid.addWidget(card, row, col)
