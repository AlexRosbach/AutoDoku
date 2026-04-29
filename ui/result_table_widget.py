"""Inline-editable result table – the central working document of AutoDoku.

Each row represents one discovered Device.  Editable cells are white;
auto-suggested values (not yet confirmed by the user) are shown with a
yellow background and italic font – exactly like the user expects.

Double-clicking any row opens the full DeviceEditDialog for peripheral
management, detailed hardware fields and other complex edits.
"""
from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
)

from core.suggestions import suggest, completion_score
from data.models import (
    CMDB_STATUSES,
    DEVICE_TYPE_FROM_LABEL,
    DEVICE_TYPE_LABELS,
    Device,
    DeviceType,
    ScanStatus,
)
from ui.lang import t, register as lang_register

logger = logging.getLogger(__name__)

# ── Colours ────────────────────────────────────────────────────────────────
_COL_SUGGESTION  = QColor("#4a3d00")   # dark amber – yellow suggestion cells
_COL_FG_SUGGEST  = QColor("#ffd966")   # bright yellow text
_COL_READONLY    = QColor("#1a1a1a")   # very dark – read-only cells
_COL_FG_READONLY = QColor("#888888")
_COL_NORMAL      = QColor("#252526")   # editable default

_COL_STATUS_SCANNING = QColor("#1a3a5c")
_COL_STATUS_DONE     = QColor("#1a3a1a")
_COL_STATUS_FAILED   = QColor("#3a1a1a")
_COL_STATUS_PENDING  = QColor("#2a2a2a")

_FG_STATUS_SCANNING  = QColor("#5b9bd5")
_FG_STATUS_DONE      = QColor("#70c842")
_FG_STATUS_FAILED    = QColor("#f44336")
_FG_STATUS_PENDING   = QColor("#888888")

_COL_PERIPH_PENDING  = QColor("#4a3d00")   # amber bg for pending suggestions
_FG_PERIPH_PENDING   = QColor("#ffd966")

# Custom item roles
_ROLE_FIELD      = Qt.ItemDataRole.UserRole        # field name str
_ROLE_DEVICE_ID  = Qt.ItemDataRole.UserRole + 1   # device id str
_ROLE_SUGGESTED  = Qt.ItemDataRole.UserRole + 2   # bool – still a suggestion?
_ROLE_USER_EDIT  = Qt.ItemDataRole.UserRole + 3   # bool – user has edited?

# ── Column definitions ─────────────────────────────────────────────────────
# (lang_key, field, editable, min_width, is_dropdown)
# field == "__peripherals__" is a synthetic column rendered from device.peripherals
_COLS: list[tuple[str, str | None, bool, int, bool]] = [
    ("col_status",       "scan_status",     False,  80, False),
    ("col_peripherals",  "__peripherals__", False,  90, False),
    ("col_type",         "device_type",     True,   90, True),   # ComboBox
    ("col_ip",           "ip",              False, 115, False),
    ("col_mac",          "mac",             False, 135, False),
    ("col_manufacturer", "manufacturer",    True,  130, False),
    ("col_hostname",     "hostname",        True,  150, False),
    ("col_os",           "os",              True,  150, False),
    ("col_cpu",          "cpu",             True,  160, False),
    ("col_ram",          "ram_gb",          False,  70, False),
    ("col_model",        "model",           True,  130, False),
    ("col_serial",       "serial",          True,  115, False),
    ("col_location",     "location",        True,  110, False),
    ("col_room",         "room",            True,   70, False),
    ("col_department",   "department",      True,  110, False),
    ("col_contact",      "contact",         True,  110, False),
    ("col_cmdb_status",  "cmdb_status",     True,  110, True),   # ComboBox
    ("col_sysid",        "sysid",           True,   90, False),
    ("col_notes",        "notes",           True,  180, False),
]

# Lookup from field name to column index (built once)
_FIELD_TO_COL: dict[str, int] = {c[1]: i for i, c in enumerate(_COLS) if c[1]}


class _ComboDelegate(QStyledItemDelegate):
    """Shows a QComboBox for dropdown columns."""

    def __init__(self, options: list[str], parent=None) -> None:
        super().__init__(parent)
        self._options = options

    def createEditor(self, parent, option: QStyleOptionViewItem, index):
        cb = QComboBox(parent)
        cb.addItems(self._options)
        return cb

    def setEditorData(self, editor: QComboBox, index) -> None:
        val = index.data(Qt.ItemDataRole.EditRole) or ""
        idx = editor.findText(val)
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor: QComboBox, model, index) -> None:
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        editor.setGeometry(option.rect)


class ResultTableWidget(QTableWidget):
    """Inline-editable device table with suggestion highlighting.

    Signals:
        device_edit_requested(Device):  Double-click on any row.
        device_changed(Device):         Any inline cell was edited.
    """

    device_edit_requested = pyqtSignal(object)
    device_changed        = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(_COLS), parent)
        self._devices: dict[str, Device] = {}   # device_id → Device
        self._order: list[str] = []             # ordered device_ids
        self._store = None                      # kept for API compatibility
        self._block_signals = False
        self._setup_table()
        lang_register(self.retranslate)

    def set_store(self, store) -> None:
        """Kept for API compatibility – no longer used (no local storage)."""
        pass

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_table(self) -> None:
        self.setHorizontalHeaderLabels([t(c[0]) for c in _COLS])
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        self.setGridStyle(Qt.PenStyle.SolidLine)

        hdr = self.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setMinimumSectionSize(60)
        for i, (_, _, _, w, _) in enumerate(_COLS):
            hdr.resizeSection(i, w)
        # No Stretch modes on individual columns – users can freely resize them all

        # ComboBox delegates
        typ_col  = _FIELD_TO_COL.get("device_type", 2)
        cmdb_col = _FIELD_TO_COL.get("cmdb_status", 16)
        self.setItemDelegateForColumn(
            typ_col, _ComboDelegate(list(DEVICE_TYPE_LABELS.values()), self)
        )
        self.setItemDelegateForColumn(
            cmdb_col, _ComboDelegate(CMDB_STATUSES, self)
        )

        self.setSortingEnabled(True)
        self.cellDoubleClicked.connect(self._on_double_click)
        self.itemChanged.connect(self._on_item_changed)

    def retranslate(self) -> None:
        """Update all column headers to the currently active language."""
        self.setHorizontalHeaderLabels([t(c[0]) for c in _COLS])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_device(self, device: Device) -> None:
        self._block_signals = True
        # Disable sorting during row insertion: with sorting enabled Qt re-orders
        # rows mid-population, causing setItem(row, col) to target wrong cells.
        self.setSortingEnabled(False)
        self._devices[device.id] = device
        self._order.append(device.id)
        row = self.rowCount()
        self.insertRow(row)
        suggestions = suggest(device)
        self._populate_row(row, device, suggestions)
        self.setSortingEnabled(True)
        self.scrollToBottom()
        self._block_signals = False

    def update_device(self, device: Device) -> None:
        """Update a row when scan completes or external edit is saved."""
        if device.id not in self._devices:
            return
        self._devices[device.id] = device
        row = self._row_for(device.id)
        if row < 0:
            return
        self._block_signals = True
        self.setSortingEnabled(False)
        suggestions = suggest(device)
        for col, (_, field, editable, _, _) in enumerate(_COLS):
            if field is None:
                continue
            item = self.item(row, col)
            if item and item.data(_ROLE_USER_EDIT):
                continue   # user already edited this cell – leave it alone
            self._set_cell(row, col, device, field, editable, suggestions)
        self.setSortingEnabled(True)
        self._block_signals = False

    def clear_devices(self) -> None:
        self._block_signals = True
        self.setRowCount(0)
        self._devices.clear()
        self._order.clear()
        self._block_signals = False

    def get_devices(self) -> list[Device]:
        return [self._devices[did] for did in self._order if did in self._devices]

    def apply_filter(self, device_type: str = "", text: str = "") -> None:
        """Show only rows that match *device_type* and/or *text*.

        Args:
            device_type: i-doit constant (e.g. ``DeviceType.CLIENT.value``)
                         or ``""`` to show all types.
            text:        Case-insensitive substring searched across IP, hostname,
                         MAC, manufacturer, model, serial, OS, location, department.
        """
        text = text.strip().lower()
        ip_col = _FIELD_TO_COL.get("ip", 3)

        for row in range(self.rowCount()):
            item = self.item(row, ip_col)
            if not item:
                self.setRowHidden(row, False)
                continue

            device_id = item.data(_ROLE_DEVICE_ID)
            device = self._devices.get(device_id)
            if not device:
                self.setRowHidden(row, False)
                continue

            # ── Type filter ───────────────────────────────────────────
            if device_type and device.device_type != device_type:
                self.setRowHidden(row, True)
                continue

            # ── Text filter ───────────────────────────────────────────
            if text:
                haystack = " ".join(filter(None, [
                    device.ip, device.hostname, device.mac,
                    device.manufacturer, device.model, device.serial,
                    device.os, device.cpu, device.location,
                    device.room, device.department, device.contact,
                ])).lower()
                if text not in haystack:
                    self.setRowHidden(row, True)
                    continue

            self.setRowHidden(row, False)

    # ------------------------------------------------------------------
    # Row building
    # ------------------------------------------------------------------

    def _populate_row(self, row: int, device: Device, suggestions: dict[str, str]) -> None:
        for col, (_, field, editable, _, _) in enumerate(_COLS):
            self._set_cell(row, col, device, field, editable, suggestions)

    def _set_cell(
        self,
        row: int,
        col: int,
        device: Device,
        field: str | None,
        editable: bool,
        suggestions: dict[str, str],
    ) -> None:
        # ── Special: scan status column ──────────────────────────────────
        if field == "scan_status":
            status = device.scan_status
            if status == ScanStatus.DONE.value:
                method = getattr(device, "scan_method", "") or ""
                label = {
                    "wmi":   "WMI",
                    "ssh":   "SSH",
                    "snmp":  "SNMP",
                    "basic": "Basic",
                }.get(method, "Done")
                text = f"  \u2713  {label}"
                bg, fg = _COL_STATUS_DONE, _FG_STATUS_DONE
            elif status == ScanStatus.SCANNING.value:
                text, bg, fg = "  \u27f3  Scanning\u2026", _COL_STATUS_SCANNING, _FG_STATUS_SCANNING
            elif status == ScanStatus.FAILED.value:
                text, bg, fg = "  \u2717  Error", _COL_STATUS_FAILED, _FG_STATUS_FAILED
            else:
                text, bg, fg = "  \u2026  Pending", _COL_STATUS_PENDING, _FG_STATUS_PENDING

            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setData(_ROLE_DEVICE_ID, device.id)
            item.setBackground(QBrush(bg))
            item.setForeground(QBrush(fg))
            font = item.font(); font.setBold(True); item.setFont(font)
            self.setItem(row, col, item)
            return

        # ── Special: peripherals indicator column ────────────────────────
        if field == "__peripherals__":
            peripherals = device.peripherals
            pending = [p for p in peripherals if p.is_suggestion]
            confirmed = [p for p in peripherals if not p.is_suggestion]

            if pending:
                n = len(pending)
                label = t("periph_suggestion").format(n=n)
                if confirmed:
                    label += f"  +{len(confirmed)}"
                bg, fg = _COL_PERIPH_PENDING, _FG_PERIPH_PENDING
                tooltip = (
                    f"{n} peripheral suggestion(s) pending — "
                    "double-click to review"
                )
                italic = True
            elif confirmed:
                n = len(confirmed)
                label = t("periph_count").format(n=n)
                bg, fg = _COL_NORMAL, QColor("#c0c0c0")
                tooltip = f"{n} peripheral(s) documented"
                italic = False
            else:
                label = ""
                bg, fg = _COL_READONLY, _COL_FG_READONLY
                tooltip = ""
                italic = False

            item = QTableWidgetItem(label)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setData(_ROLE_DEVICE_ID, device.id)
            item.setData(_ROLE_FIELD, field)
            item.setBackground(QBrush(bg))
            item.setForeground(QBrush(fg))
            if italic:
                font = item.font(); font.setItalic(True); item.setFont(font)
            if tooltip:
                item.setToolTip(tooltip)
            self.setItem(row, col, item)
            return

        # ── Normal field ─────────────────────────────────────────────────
        raw = getattr(device, field, "") if field else ""
        raw_value = "" if raw is None else str(raw)

        # Map i-doit constant to display label for dropdown fields
        if field == "device_type":
            raw_value = DEVICE_TYPE_LABELS.get(raw_value, raw_value)

        is_suggested = False
        display_value = raw_value

        if editable and not raw_value and field in suggestions:
            display_value = suggestions[field]
            if field == "device_type":
                display_value = DEVICE_TYPE_LABELS.get(
                    suggestions[field], suggestions[field]
                )
            is_suggested = True

        item = QTableWidgetItem(display_value)
        item.setData(_ROLE_FIELD, field)
        item.setData(_ROLE_DEVICE_ID, device.id)
        item.setData(_ROLE_SUGGESTED, is_suggested)
        item.setData(_ROLE_USER_EDIT, False)

        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setBackground(QBrush(_COL_READONLY))
            item.setForeground(QBrush(_COL_FG_READONLY))
        elif is_suggested:
            item.setBackground(QBrush(_COL_SUGGESTION))
            item.setForeground(QBrush(_COL_FG_SUGGEST))
            font = item.font(); font.setItalic(True); item.setFont(font)
            item.setToolTip("Auto-suggestion — please review and adjust if needed")
        else:
            item.setBackground(QBrush(_COL_NORMAL))

        self.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Cell edit handler
    # ------------------------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._block_signals:
            return

        device_id = item.data(_ROLE_DEVICE_ID)
        field     = item.data(_ROLE_FIELD)
        if not device_id or not field:
            return
        if field in ("scan_status", "__peripherals__"):
            return   # read-only synthetic fields

        device = self._devices.get(device_id)
        if device is None:
            return

        # Mark as user-edited → remove suggestion style
        item.setData(_ROLE_USER_EDIT, True)
        item.setData(_ROLE_SUGGESTED, False)
        self._block_signals = True
        item.setBackground(QBrush(_COL_NORMAL))
        item.setForeground(self.palette().text())
        font = item.font(); font.setItalic(False); item.setFont(font)
        self._block_signals = False

        value = item.text().strip()

        # Map display label back to i-doit constant for device_type
        if field == "device_type":
            value = DEVICE_TYPE_FROM_LABEL.get(value, value)

        setattr(device, field, value)
        self.device_changed.emit(device)

    # ------------------------------------------------------------------
    # Double-click → full edit dialog
    # ------------------------------------------------------------------

    def _on_double_click(self, row: int, _col: int) -> None:
        # Read device_id from the item's custom role (works regardless of sort order)
        did = self._device_id_at_row(row)
        if did:
            device = self._devices.get(did)
            if device:
                self.device_edit_requested.emit(device)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _device_id_at_row(self, row: int) -> str | None:
        """Return the device ID stored in any non-status cell of *row*."""
        # IP column always carries _ROLE_DEVICE_ID and is never None
        ip_col = _FIELD_TO_COL.get("ip", 3)
        item = self.item(row, ip_col)
        if item:
            return item.data(_ROLE_DEVICE_ID)
        # Fallback: scan other columns
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                did = item.data(_ROLE_DEVICE_ID)
                if did:
                    return did
        return None

    def _row_for(self, device_id: str) -> int:
        """Find the current visual row for *device_id* by scanning _ROLE_DEVICE_ID.

        This is correct even after the user sorts the table, unlike using
        _order.index() which only reflects insertion order.
        """
        ip_col = _FIELD_TO_COL.get("ip", 3)
        for row in range(self.rowCount()):
            item = self.item(row, ip_col)
            if item and item.data(_ROLE_DEVICE_ID) == device_id:
                return row
        return -1
