"""Dialog for adding and managing peripherals attached to a Client device.

Supports all common peripheral types:
  Monitor, Tastatur, Maus, Headset, Docking Station, Telefon/VoIP, Drucker (lokal),
  USB-Hub, Webcam, Sonstiges.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from data.models import PERIPHERAL_TYPES, Peripheral

logger = logging.getLogger(__name__)


class PeripheralDialog(QDialog):
    """Modal dialog that collects all fields for one Peripheral record.

    Call :meth:`get_peripheral` after ``exec()`` returns ``Accepted``.
    """

    def __init__(
        self,
        device_id: str,
        peripheral: Peripheral | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._device_id = device_id
        self._existing  = peripheral
        self.setWindowTitle(
            "Edit Peripheral" if peripheral else "Add Peripheral"
        )
        self.setMinimumWidth(380)
        self._build_ui()
        if peripheral:
            self._load(peripheral)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._type = QComboBox()
        self._type.addItems(PERIPHERAL_TYPES)
        form.addRow(QLabel("Type:"), self._type)

        self._manufacturer = QLineEdit()
        self._manufacturer.setPlaceholderText("e.g. Dell, HP, Logitech …")
        form.addRow(QLabel("Manufacturer:"), self._manufacturer)

        self._model = QLineEdit()
        self._model.setPlaceholderText("e.g. U2722D, MX Keys …")
        form.addRow(QLabel("Model:"), self._model)

        self._serial = QLineEdit()
        self._serial.setPlaceholderText("Serial number (optional)")
        form.addRow(QLabel("Serial No.:"), self._serial)

        self._notes = QLineEdit()
        self._notes.setPlaceholderText("Additional notes (optional)")
        form.addRow(QLabel("Notes:"), self._notes)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load(self, p: Peripheral) -> None:
        idx = self._type.findText(p.peripheral_type)
        if idx >= 0:
            self._type.setCurrentIndex(idx)
        self._manufacturer.setText(p.manufacturer)
        self._model.setText(p.model)
        self._serial.setText(p.serial)
        self._notes.setText(p.notes)

    def get_peripheral(self) -> Peripheral:
        pid = self._existing.id if self._existing else None
        return Peripheral(
            id=pid or __import__("uuid").uuid4().__str__(),
            device_id=self._device_id,
            peripheral_type=self._type.currentText(),
            manufacturer=self._manufacturer.text().strip(),
            model=self._model.text().strip(),
            serial=self._serial.text().strip(),
            notes=self._notes.text().strip(),
        )


