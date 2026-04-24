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
from ui.peripheral_dialog import PeripheralDialog

logger = logging.getLogger(__name__)

# Styles are defined in dark_theme.qss via object names (suggestionField, suggestionBadge, etc.)


class DeviceEditDialog(QDialog):
    """Modal dialog for reviewing and editing a Device's documentation."""

    def __init__(self, device: Device, parent=None) -> None:
        super().__init__(parent)
        self._device = device
        # Work on a shallow copy of the list so we can cancel changes
        self._peripherals: list[Peripheral] = list(device.peripherals)
        self._suggestions = suggest(device)
        filled, total = completion_score(device)

        title = device.hostname or device.ip
        self.setWindowTitle(f"Edit Device – {title}")
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
        bar_label = QLabel(f"Completion: {filled}/{total} fields  ({pct} %)")
        bar_label.setObjectName("completionLabel")
        bar_label.setStyleSheet(f"color: {bar_color};")   # dynamic color stays inline
        bar_layout.addWidget(bar_label)
        bar_layout.addStretch()
        if self._suggestions:
            hint = QLabel(f"🟡 {len(self._suggestions)} suggestion(s) available")
            hint.setObjectName("suggestionHint")
            bar_layout.addWidget(hint)
        layout.addWidget(bar_widget)

        tabs = QTabWidget()
        tabs.addTab(self._build_scan_tab(),  "🔍 Scan Result")
        tabs.addTab(self._build_docs_tab(),  "📋 Documentation")
        if self._device.device_type == DeviceType.CLIENT.value:
            tabs.addTab(self._build_peripheral_tab(), "🖱 Peripherals")
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

        hw_box = QGroupBox("Identity (from scan)")
        form = QFormLayout(hw_box)
        for label, value in [
            ("IP Address:",  self._device.ip),
            ("MAC Address:", self._device.mac),
            ("Hostname:",    self._device.hostname),
            ("Manufacturer:", self._device.manufacturer),
            ("Device Type:", DEVICE_TYPE_LABELS.get(self._device.device_type, self._device.device_type)),
        ]:
            lbl = QLabel(value or "–")
            lbl.setObjectName("scanValue")
            form.addRow(QLabel(label), lbl)
        layout.addWidget(hw_box)

        hw2_box = QGroupBox("Hardware (Deep Scan)")
        form2 = QFormLayout(hw2_box)
        for label, value in [
            ("Operating System:", self._device.os),
            ("CPU:",              self._device.cpu),
            ("RAM (GB):",         str(self._device.ram_gb) if self._device.ram_gb else "–"),
            ("Model:",            self._device.model),
            ("Serial No.:",       self._device.serial),
        ]:
            lbl = QLabel(value or "–")
            lbl.setObjectName("scanValue")
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

        # Device type (dropdown)
        self._device_type_cb = QComboBox()
        self._device_type_cb.addItems(list(DEVICE_TYPE_LABELS.values()))
        cur_label = DEVICE_TYPE_LABELS.get(self._device.device_type, "Unknown")
        self._device_type_cb.setCurrentText(cur_label)
        form.addRow(QLabel("Device Type:"), self._device_type_cb)

        # CMDB Status (dropdown)
        self._cmdb_cb = QComboBox()
        self._cmdb_cb.addItems(CMDB_STATUSES)
        cmdb_val = self._device.cmdb_status
        if not cmdb_val and "cmdb_status" in self._suggestions:
            cmdb_val = self._suggestions["cmdb_status"]
        self._cmdb_cb.setCurrentText(cmdb_val or CMDB_STATUSES[0])
        form.addRow(QLabel("CMDB Status:"), self._cmdb_cb)

        # All other text fields
        field_defs = [
            ("inventory_no", "Inventory No.:",  "e.g. IT-2024-001"),
            ("sysid",        "Sysid (i-doit):", "i-doit object ID – used to update on re-import"),
            ("serial",       "Serial No.:",     ""),
            ("location",     "Location:",       "e.g. Building A"),
            ("room",         "Room:",           "e.g. 2.15"),
            ("department",   "Department:",     "e.g. IT"),
            ("contact",      "Contact:",        "e.g. John Smith"),
            ("os",           "Operating System:", ""),
            ("model",        "Model:",          ""),
            ("manufacturer", "Manufacturer:",   ""),
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
                edit.setObjectName("suggestionField")
                edit.setToolTip("Auto-suggestion — please confirm or adjust")
                edit.textEdited.connect(lambda _, e=edit: e.setObjectName("") or e.setStyleSheet(""))
            self._fields[attr] = edit

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(edit)
            if is_suggestion:
                badge = QLabel("Suggestion")
                badge.setObjectName("suggestionBadge")
                row_layout.addWidget(badge)

            form.addRow(QLabel(label), row_widget)

        # Notes (multi-line)
        self._notes = QTextEdit(self._device.notes)
        self._notes.setFixedHeight(60)
        self._notes.setPlaceholderText("Free-form notes …")
        form.addRow(QLabel("Notes:"), self._notes)

        layout.addLayout(form)
        layout.addStretch()
        return w

    # ── Tab: Peripherie ────────────────────────────────────────────────

    def _build_peripheral_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # ── Suggestion banner ──────────────────────────────────────────
        pending = [p for p in self._peripherals if p.is_suggestion]
        if pending:
            banner = QLabel(
                f"🟡  {len(pending)} peripheral suggestion(s) — "
                "please review, add model / serial and confirm."
            )
            banner.setWordWrap(True)
            banner.setStyleSheet(
                "background: #4a3d00; color: #ffd966; "
                "padding: 8px 10px; border-radius: 3px; "
                "font-weight: bold;"
            )
            layout.addWidget(banner)

        hint = QLabel(
            "Add all devices connected to this client.\n"
            "Monitors, keyboards, mice, headsets, docking stations, etc.\n"
            "Each item is exported as a separate i-doit object in the CSV."
        )
        hint.setWordWrap(True)
        hint.setObjectName("statsHint")
        layout.addWidget(hint)

        self._periph_list = QListWidget()
        self._periph_list.setAlternatingRowColors(True)
        self._refresh_peripheral_list()
        layout.addWidget(self._periph_list)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        btn_add = QPushButton("➕  Add")
        btn_add.clicked.connect(self._add_peripheral)
        btn_edit = QPushButton("✏  Edit")
        btn_edit.setObjectName("btnSecondary")
        btn_edit.clicked.connect(self._edit_peripheral)
        btn_del = QPushButton("🗑  Remove")
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
            parts = [p.peripheral_type]
            details = " ".join(filter(None, [p.manufacturer, p.model]))
            if details:
                parts.append(details)
            label = "  ·  ".join(parts)
            if p.serial:
                label += f"  [{p.serial}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            # Mark auto-suggested peripherals visually
            if p.is_suggestion:
                item.setForeground(QColor("#ffd966"))
                item.setToolTip("Auto-suggestion — please add model / serial number and confirm")
            self._periph_list.addItem(item)

    def _add_peripheral(self) -> None:
        dlg = PeripheralDialog(self._device.id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            p = dlg.get_peripheral()
            self._peripherals.append(p)
            self._refresh_peripheral_list()

    def _edit_peripheral(self) -> None:
        row = self._periph_list.currentRow()
        if 0 <= row < len(self._peripherals):
            p = self._peripherals[row]
            dlg = PeripheralDialog(self._device.id, peripheral=p, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                updated = dlg.get_peripheral()
                updated.is_suggestion = False   # user confirmed / edited → no longer a suggestion
                self._peripherals[row] = updated
                self._refresh_peripheral_list()

    def _remove_peripheral(self) -> None:
        row = self._periph_list.currentRow()
        if 0 <= row < len(self._peripherals):
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

        # Write peripherals back to the device (in-memory, no DB)
        self._device.peripherals = list(self._peripherals)

        return self._device
