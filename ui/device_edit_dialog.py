"""Dialog for reviewing and editing the metadata of a discovered device."""
from __future__ import annotations
import logging

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from data.models import Device, DeviceType, Monitor
from data.session_store import SessionStore
from ui.monitor_suggest_dialog import MonitorSuggestDialog

logger = logging.getLogger(__name__)


class DeviceEditDialog(QDialog):
    """Modal dialog that shows device details and lets the user fill in
    location, department, serial, notes, and — for CLIENT devices — monitors.
    """

    def __init__(self, device: Device, store: SessionStore, parent=None) -> None:
        super().__init__(parent)
        self._device = device
        self._store = store
        self.setWindowTitle(f"Gerät bearbeiten – {device.hostname or device.ip}")
        self.setMinimumWidth(480)
        self._monitors: list[Monitor] = store.load_monitors_for_device(device.id)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── Read-only info ───────────────────────────────────────────
        info = QGroupBox("Geräteinformationen")
        info_form = QFormLayout(info)
        for label, value in [
            ("IP-Adresse:", self._device.ip),
            ("MAC-Adresse:", self._device.mac),
            ("Hostname:", self._device.hostname),
            ("Typ:", self._device.device_type),
            ("Betriebssystem:", self._device.os),
            ("Hersteller:", self._device.manufacturer),
            ("Modell:", self._device.model),
            ("CPU:", self._device.cpu),
            ("RAM (GB):", str(self._device.ram_gb) if self._device.ram_gb else ""),
        ]:
            lbl = QLabel(value)
            lbl.setStyleSheet("color: #aaa;")
            info_form.addRow(QLabel(label), lbl)
        layout.addWidget(info)

        # ── Editable fields ──────────────────────────────────────────
        edit = QGroupBox("Bearbeitbare Felder")
        edit_form = QFormLayout(edit)

        self._location = QLineEdit(self._device.location)
        self._department = QLineEdit(self._device.department)
        self._serial = QLineEdit(self._device.serial)
        self._notes = QTextEdit(self._device.notes)
        self._notes.setFixedHeight(70)

        edit_form.addRow(QLabel("Standort:"), self._location)
        edit_form.addRow(QLabel("Abteilung:"), self._department)
        edit_form.addRow(QLabel("Seriennummer:"), self._serial)
        edit_form.addRow(QLabel("Notizen:"), self._notes)
        layout.addWidget(edit)

        # ── Monitor section (CLIENT only) ────────────────────────────
        if self._device.device_type == DeviceType.CLIENT.value:
            mon_group = QGroupBox("Monitore")
            mon_layout = QVBoxLayout(mon_group)

            self._monitor_list = QListWidget()
            self._refresh_monitor_list()
            mon_layout.addWidget(self._monitor_list)

            btn_add = QPushButton("Monitor hinzufügen")
            btn_add.clicked.connect(self._add_monitor)
            mon_layout.addWidget(btn_add)
            layout.addWidget(mon_group)

        # ── Buttons ──────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_monitor_list(self) -> None:
        self._monitor_list.clear()
        for m in self._monitors:
            label = f"{m.manufacturer} {m.model}".strip() or m.serial or "Unbekannt"
            self._monitor_list.addItem(QListWidgetItem(label))

    def _add_monitor(self) -> None:
        dlg = MonitorSuggestDialog(self._device.id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            monitor = dlg.get_monitor()
            self._store.save_monitor(monitor)
            self._monitors.append(monitor)
            self._refresh_monitor_list()

    def apply(self) -> Device:
        """Write form values back to the Device and return it."""
        self._device.location = self._location.text().strip()
        self._device.department = self._department.text().strip()
        self._device.serial = self._serial.text().strip()
        self._device.notes = self._notes.toPlainText().strip()
        return self._device
