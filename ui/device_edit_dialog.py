"""Full device-edit dialog with all i-doit documentation fields.

Structured in three tabs:
  • Identifikation   – scan results (read-only overview)
  • Dokumentation    – all i-doit fields with proactive suggestions
  • Peripherie       – attached peripherals (CLIENT only)
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.suggestions import suggest, completion_score
from data.models import (
    CMDB_STATUSES,
    DEVICE_TYPE_LABELS,
    DEVICE_TYPE_FROM_LABEL,
    Device,
    DeviceType,
    Peripheral,
)
from data.session_store import SessionStore
from ui.peripheral_dialog import PeripheralDialog

logger = logging.getLogger(__name__)

_SUGGESTION_STYLE = "background:#4a3d00; color:#ffd966; border:1px solid #7a6200; border-radius:3px; padding:3px 6px;"
_LABEL_HINT_STYLE = "color:#ffd966; font-size:11px; font-style:italic;"


class DeviceEditDialog(QDialog):
    """Modal dialog for reviewing and editing a Device's documentation."""

    def __init__(self, device: Device, store: SessionStore, parent=None) -> None:
        super().__init__(parent)
        self._device = device
        self._store  = store
        self._peripherals: list[Peripheral] = store.load_peripherals_for_device(device.id)
        self._suggestions = suggest(device)
        filled, total = completion_score(device)

        title = device.hostname or device.ip
        self.setWindowTitle(f"Gerät bearbeiten – {title}")
        self.setMinimumWidth(560)
        self.resize(600, 680)
        self._build_ui(filled, total)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self, filled: int, total: int) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Completion bar
        pct = int(filled / total * 100) if total else 0
        bar_color = "#70c842" if pct >= 80 else ("#ffd966" if pct >= 40 else "#f44336")
        bar_widget = QWidget()
        bar_layout = QHBoxLayout(bar_widget)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_label = QLabel(f"Dokumentationsgrad: {filled}/{total} Felder  ({pct} %)")
        bar_label.setStyleSheet(f"color: {bar_color}; font-weight: bold;")
        bar_layout.addWidget(bar_label)
        bar_layout.addStretch()
        if self._suggestions:
            hint = QLabel(f"🟡 {len(self._suggestions)} Vorschlag/Vorschläge verfügbar")
            hint.setStyleSheet(_LABEL_HINT_STYLE)
            bar_layout.addWidget(hint)
        layout.addWidget(bar_widget)

        tabs = QTabWidget()
        tabs.addTab(self._build_scan_tab(),  "🔍 Scan-Ergebnis")
        tabs.addTab(self._build_docs_tab(),  "📋 Dokumentation")
        if self._device.device_type == DeviceType.CLIENT.value:
            tabs.addTab(self._build_peripheral_tab(), "🖱 Peripherie")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Tab: Scan-Ergebnis ─────────────────────────────────────────────

    def _build_scan_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        hw_box = QGroupBox("Identifikation (aus Scan)")
        form = QFormLayout(hw_box)
        for label, value in [
            ("IP-Adresse:",  self._device.ip),
            ("MAC-Adresse:", self._device.mac),
            ("Hostname:",    self._device.hostname),
            ("Hersteller:",  self._device.manufacturer),
            ("Gerättyp:",    DEVICE_TYPE_LABELS.get(self._device.device_type, self._device.device_type)),
        ]:
            lbl = QLabel(value or "–")
            lbl.setStyleSheet("color: #ccc;")
            form.addRow(QLabel(label), lbl)
        layout.addWidget(hw_box)

        hw2_box = QGroupBox("Hardware (Deep-Scan)")
        form2 = QFormLayout(hw2_box)
        for label, value in [
            ("Betriebssystem:", self._device.os),
            ("CPU:",            self._device.cpu),
            ("RAM (GB):",       str(self._device.ram_gb) if self._device.ram_gb else "–"),
            ("Modell:",         self._device.model),
            ("Seriennummer:",   self._device.serial),
        ]:
            lbl = QLabel(value or "–")
            lbl.setStyleSheet("color: #ccc;")
            form2.addRow(QLabel(label), lbl)
        layout.addWidget(hw2_box)
        layout.addStretch()
        return w

    # ── Tab: Dokumentation ─────────────────────────────────────────────

    def _build_docs_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # Gerättyp (dropdown)
        self._device_type_cb = QComboBox()
        self._device_type_cb.addItems(list(DEVICE_TYPE_LABELS.values()))
        cur_label = DEVICE_TYPE_LABELS.get(self._device.device_type, "Unbekannt")
        self._device_type_cb.setCurrentText(cur_label)
        form.addRow(QLabel("Gerättyp:"), self._device_type_cb)

        # CMDB-Status (dropdown)
        self._cmdb_cb = QComboBox()
        self._cmdb_cb.addItems(CMDB_STATUSES)
        cmdb_val = self._device.cmdb_status
        if not cmdb_val and "cmdb_status" in self._suggestions:
            cmdb_val = self._suggestions["cmdb_status"]
        self._cmdb_cb.setCurrentText(cmdb_val or CMDB_STATUSES[0])
        form.addRow(QLabel("CMDB-Status:"), self._cmdb_cb)

        # All other text fields
        field_defs = [
            ("inventory_no", "Inventarnummer:",  "z. B. IT-2024-001"),
            ("serial",       "Seriennummer:",    ""),
            ("location",     "Standort:",        "z. B. Gebäude A"),
            ("room",         "Raum:",            "z. B. 2.15"),
            ("department",   "Abteilung:",       "z. B. IT"),
            ("contact",      "Ansprechpartner:", "z. B. Max Mustermann"),
            ("os",           "Betriebssystem:",  ""),
            ("model",        "Modell:",          ""),
            ("manufacturer", "Hersteller:",      ""),
        ]
        self._fields: dict[str, QLineEdit] = {}
        for attr, label, placeholder in field_defs:
            value = str(getattr(self._device, attr, "") or "")
            is_suggestion = False
            if not value and attr in self._suggestions:
                value = self._suggestions[attr]
                is_suggestion = True

            edit = QLineEdit(value)
            edit.setPlaceholderText(placeholder)
            if is_suggestion:
                edit.setStyleSheet(_SUGGESTION_STYLE)
                edit.setToolTip("Automatischer Vorschlag – bitte bestätigen oder ändern")
                edit.textEdited.connect(lambda _, e=edit: e.setStyleSheet(""))
            self._fields[attr] = edit

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(edit)
            if is_suggestion:
                badge = QLabel("Vorschlag")
                badge.setStyleSheet("color:#ffd966; font-size:10px; margin-left:4px;")
                row_layout.addWidget(badge)

            form.addRow(QLabel(label), row_widget)

        # Notes (multi-line)
        self._notes = QTextEdit(self._device.notes)
        self._notes.setFixedHeight(60)
        self._notes.setPlaceholderText("Freie Notizen zur Dokumentation …")
        form.addRow(QLabel("Notizen:"), self._notes)

        layout.addLayout(form)
        layout.addStretch()
        return w

    # ── Tab: Peripherie ────────────────────────────────────────────────

    def _build_peripheral_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        hint = QLabel(
            "Füge alle Geräte hinzu, die an diesen Client angeschlossen sind.\n"
            "Monitore, Tastaturen, Mäuse, Headsets, Docking Stations usw.\n"
            "Diese werden beim CSV-Export als separate i-doit-Objekte exportiert."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#aaa; font-size:11px;")
        layout.addWidget(hint)

        self._periph_list = QListWidget()
        self._periph_list.setAlternatingRowColors(True)
        self._refresh_peripheral_list()
        layout.addWidget(self._periph_list)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        btn_add = QPushButton("➕  Hinzufügen")
        btn_add.clicked.connect(self._add_peripheral)
        btn_edit = QPushButton("✏  Bearbeiten")
        btn_edit.setObjectName("btnSecondary")
        btn_edit.clicked.connect(self._edit_peripheral)
        btn_del = QPushButton("🗑  Entfernen")
        btn_del.setObjectName("btnSecondary")
        btn_del.clicked.connect(self._remove_peripheral)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_del)
        btn_layout.addStretch()
        layout.addWidget(btn_row)
        return w

    # ------------------------------------------------------------------
    # Peripheral actions
    # ------------------------------------------------------------------

    def _refresh_peripheral_list(self) -> None:
        self._periph_list.clear()
        for p in self._peripherals:
            label = f"{p.peripheral_type}  ·  {p.manufacturer} {p.model}".strip(" ·")
            if p.serial:
                label += f"  [{p.serial}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self._periph_list.addItem(item)

    def _add_peripheral(self) -> None:
        dlg = PeripheralDialog(self._device.id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            p = dlg.get_peripheral()
            self._store.save_peripheral(p)
            self._peripherals.append(p)
            self._refresh_peripheral_list()

    def _edit_peripheral(self) -> None:
        row = self._periph_list.currentRow()
        if 0 <= row < len(self._peripherals):
            p = self._peripherals[row]
            dlg = PeripheralDialog(self._device.id, peripheral=p, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                updated = dlg.get_peripheral()
                self._store.save_peripheral(updated)
                self._peripherals[row] = updated
                self._refresh_peripheral_list()

    def _remove_peripheral(self) -> None:
        row = self._periph_list.currentRow()
        if 0 <= row < len(self._peripherals):
            self._store.delete_peripheral(self._peripherals[row].id)
            self._peripherals.pop(row)
            self._refresh_peripheral_list()

    # ------------------------------------------------------------------
    # Apply changes
    # ------------------------------------------------------------------

    def apply(self) -> Device:
        # Device type
        label = self._device_type_cb.currentText()
        self._device.device_type = DEVICE_TYPE_FROM_LABEL.get(label, self._device.device_type)

        # CMDB status
        self._device.cmdb_status = self._cmdb_cb.currentText()

        # Text fields
        for attr, edit in self._fields.items():
            setattr(self._device, attr, edit.text().strip())

        self._device.notes = self._notes.toPlainText().strip()
        return self._device
