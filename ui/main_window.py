"""AutoDoku main application window.

Fully in-memory: no SQLite, no local storage.
Previous exports can be re-imported via "CSV importieren" to continue work.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.scanner import ScanWorker
from data.models import Device, DeviceType, ScanSession
from export import idoit_csv_exporter
from export.csv_importer import import_csv
from ui.device_edit_dialog import DeviceEditDialog
from ui.lang import get_lang, toggle_lang, t, register as lang_register
from ui.progress_widget import ProgressWidget
from ui.result_table_widget import ResultTableWidget
from ui.scan_config_dialog import ScanConfigDialog
from version import __version__, __app_name__

logger = logging.getLogger(__name__)


def _set_stat_caption(stat_widget: "QWidget", caption: str) -> None:
    """Update the caption QLabel inside a stat widget created by _make_stat_label."""
    from PyQt6.QtWidgets import QLabel
    for child in stat_widget.findChildren(QLabel):
        if child.objectName() == "statCaption":
            child.setText(caption)
            break


class MainWindow(QMainWindow):
    """Top-level window containing the scan controls, device table and export."""

    def __init__(self, config: dict) -> None:
        super().__init__()
        self._config  = config
        self._session: ScanSession | None = None
        self._worker: ScanWorker | None = None

        self.setWindowTitle(f"{__app_name__} {__version__} – {t('window_title')}")
        self.resize(1400, 820)
        self._build_ui()
        lang_register(self.retranslate)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)
        root.setContentsMargins(12, 10, 12, 10)

        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_stats_bar())
        root.addWidget(self._build_table())
        root.addWidget(self._build_bottom_bar())

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Logo / app name
        title_lbl = QLabel(f"{__app_name__}")
        title_lbl.setObjectName("appTitle")
        layout.addWidget(title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("topBarSep")
        layout.addWidget(sep)

        self._ip_range_lbl = QLabel(t("lbl_ip_range"))
        layout.addWidget(self._ip_range_lbl)
        self._ip_input = QLineEdit(self._config.get("default_ip_range", "192.168.1.0/24"))
        self._ip_input.setFixedWidth(200)
        self._ip_input.setPlaceholderText("e.g. 192.168.1.0/24")
        layout.addWidget(self._ip_input)

        self._wmi_cb  = QCheckBox("WMI")
        self._wmi_cb.setToolTip(t("tip_wmi"))
        self._ssh_cb  = QCheckBox("SSH")
        self._ssh_cb.setToolTip(t("tip_ssh"))
        self._snmp_cb = QCheckBox("SNMP")
        self._snmp_cb.setToolTip(t("tip_snmp"))
        layout.addWidget(self._wmi_cb)
        layout.addWidget(self._ssh_cb)
        layout.addWidget(self._snmp_cb)

        layout.addStretch()

        # Language toggle – switches between EN and DE
        self._lang_btn = QPushButton("🇩🇪 DE")
        self._lang_btn.setObjectName("btnSecondary")
        self._lang_btn.setFixedWidth(68)
        self._lang_btn.setToolTip("Switch language / Sprache wechseln")
        self._lang_btn.clicked.connect(self._toggle_language)
        layout.addWidget(self._lang_btn)

        self._config_btn = QPushButton(t("btn_config"))
        self._config_btn.setObjectName("btnSecondary")
        self._config_btn.clicked.connect(self._open_config)
        layout.addWidget(self._config_btn)

        self._scan_btn = QPushButton(t("btn_scan"))
        self._scan_btn.clicked.connect(self._start_scan)
        layout.addWidget(self._scan_btn)

        self._stop_btn = QPushButton(t("btn_stop"))
        self._stop_btn.setObjectName("btnSecondary")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_scan)
        layout.addWidget(self._stop_btn)

        return bar

    def _build_stats_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("statsBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(20)

        self._stat_total    = self._make_stat_label(t("stat_total"),    "0")
        self._stat_clients  = self._make_stat_label(t("stat_clients"),  "0", "#5b9bd5")
        self._stat_servers  = self._make_stat_label(t("stat_servers"),  "0", "#70c842")
        self._stat_switches = self._make_stat_label(t("stat_switches"), "0", "#ffd966")
        self._stat_printers = self._make_stat_label(t("stat_printers"), "0", "#cc88ff")
        self._stat_other    = self._make_stat_label(t("stat_other"),    "0", "#888")

        for w in (self._stat_total, self._stat_clients, self._stat_servers,
                  self._stat_switches, self._stat_printers, self._stat_other):
            layout.addWidget(w)

        layout.addStretch()
        self._hint_lbl = QLabel(t("hint_dblclick"))
        self._hint_lbl.setObjectName("statsHint")
        layout.addWidget(self._hint_lbl)

        return bar

    @staticmethod
    def _make_stat_label(caption: str, value: str, color: str = "#e0e0e0") -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        val_lbl = QLabel(value)
        val_lbl.setObjectName("statValue")
        val_lbl.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
        cap_lbl = QLabel(caption)
        cap_lbl.setObjectName("statCaption")
        h.addWidget(val_lbl)
        h.addWidget(cap_lbl)
        w._value_lbl = val_lbl  # type: ignore[attr-defined]
        return w

    def _build_table(self) -> ResultTableWidget:
        self._table = ResultTableWidget()
        self._table.device_edit_requested.connect(self._open_device_edit)
        self._table.device_changed.connect(self._on_device_changed)
        return self._table

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)

        self._progress = ProgressWidget()
        self._progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._progress)

        self._import_btn = QPushButton(t("btn_import"))
        self._import_btn.setObjectName("btnSecondary")
        self._import_btn.setToolTip(t("tip_import"))
        self._import_btn.clicked.connect(self._import_csv)
        layout.addWidget(self._import_btn)

        self._export_btn = QPushButton(t("btn_export"))
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_csv)
        layout.addWidget(self._export_btn)

        return bar

    # ------------------------------------------------------------------
    # Stats helpers
    # ------------------------------------------------------------------

    def _update_stats(self) -> None:
        devices = self._table.get_devices()
        total    = len(devices)
        clients  = sum(1 for d in devices if d.device_type == DeviceType.CLIENT.value)
        servers  = sum(1 for d in devices if d.device_type == DeviceType.SERVER.value)
        switches = sum(1 for d in devices if d.device_type == DeviceType.SWITCH.value)
        printers = sum(1 for d in devices if d.device_type == DeviceType.PRINTER.value)
        other    = total - clients - servers - switches - printers

        self._stat_total._value_lbl.setText(str(total))       # type: ignore[attr-defined]
        self._stat_clients._value_lbl.setText(str(clients))   # type: ignore[attr-defined]
        self._stat_servers._value_lbl.setText(str(servers))   # type: ignore[attr-defined]
        self._stat_switches._value_lbl.setText(str(switches)) # type: ignore[attr-defined]
        self._stat_printers._value_lbl.setText(str(printers)) # type: ignore[attr-defined]
        self._stat_other._value_lbl.setText(str(other))       # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Scan lifecycle
    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        ip_range = self._ip_input.text().strip()
        if not ip_range:
            QMessageBox.warning(self, "Error", "Please enter an IP range.")
            return

        self._table.clear_devices()
        self._export_btn.setEnabled(False)
        self._progress.reset()
        self._update_stats()

        now = datetime.now(tz=timezone.utc).isoformat()
        self._session = ScanSession(
            ip_range=ip_range,
            created_at=now,
            name=f"Scan {ip_range} – {now[:10]}",
        )

        self._worker = ScanWorker(
            session=self._session,
            config=self._config,
            use_wmi=self._wmi_cb.isChecked(),
            use_ssh=self._ssh_cb.isChecked(),
            use_snmp=self._snmp_cb.isChecked(),
            parent=self,
        )
        self._worker.progress.connect(self._progress.set_progress)
        self._worker.device_found.connect(self._on_device_found)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.error.connect(self._on_scan_error)

        self._scan_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._worker.start()

    def _stop_scan(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._stop_btn.setEnabled(False)

    def _on_device_found(self, device: Device) -> None:
        self._table.add_device(device)
        self._update_stats()

    def _on_scan_finished(self) -> None:
        self._scan_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        devices = self._table.get_devices()
        count = len(devices)
        if count > 0:
            self._export_btn.setEnabled(True)

        clients = sum(1 for d in devices if d.device_type == DeviceType.CLIENT.value)
        servers = sum(1 for d in devices if d.device_type == DeviceType.SERVER.value)
        parts = [f"{count} device(s) found"]
        if clients:
            parts.append(f"{clients} client(s)")
        if servers:
            parts.append(f"{servers} server(s)")
        msg = " · ".join(parts) + " — cells editable inline · double-click for full details"
        self._progress.set_progress(100, msg)
        self._update_stats()

    def _on_scan_error(self, message: str) -> None:
        self._scan_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Scan Error", message)

    def _on_device_changed(self, device: Device) -> None:
        self._update_stats()

    # ------------------------------------------------------------------
    # Device editing
    # ------------------------------------------------------------------

    def _open_device_edit(self, device: Device) -> None:
        dlg = DeviceEditDialog(device, parent=self)
        if dlg.exec() == DeviceEditDialog.DialogCode.Accepted:
            updated = dlg.apply()
            self._table.update_device(updated)
            if self._session:
                for i, d in enumerate(self._session.devices):
                    if d.id == updated.id:
                        self._session.devices[i] = updated
                        break
            self._update_stats()

    # ------------------------------------------------------------------
    # Language toggle
    # ------------------------------------------------------------------

    def _toggle_language(self) -> None:
        new_lang = toggle_lang()   # switches and notifies all callbacks
        # Button shows the *other* language (what you'll switch TO next)
        self._lang_btn.setText("🇩🇪 DE" if new_lang == "EN" else "🇬🇧 EN")

    def retranslate(self) -> None:
        """Update all translatable strings in the main window."""
        self.setWindowTitle(f"{__app_name__} {__version__} – {t('window_title')}")
        self._ip_range_lbl.setText(t("lbl_ip_range"))
        self._wmi_cb.setToolTip(t("tip_wmi"))
        self._ssh_cb.setToolTip(t("tip_ssh"))
        self._snmp_cb.setToolTip(t("tip_snmp"))
        self._config_btn.setText(t("btn_config"))
        self._scan_btn.setText(t("btn_scan"))
        self._stop_btn.setText(t("btn_stop"))
        self._import_btn.setText(t("btn_import"))
        self._import_btn.setToolTip(t("tip_import"))
        self._export_btn.setText(t("btn_export"))
        self._hint_lbl.setText(t("hint_dblclick"))
        # Stats captions
        _set_stat_caption(self._stat_total,    t("stat_total"))
        _set_stat_caption(self._stat_clients,  t("stat_clients"))
        _set_stat_caption(self._stat_servers,  t("stat_servers"))
        _set_stat_caption(self._stat_switches, t("stat_switches"))
        _set_stat_caption(self._stat_printers, t("stat_printers"))
        _set_stat_caption(self._stat_other,    t("stat_other"))
        # Table column headers (ResultTableWidget handles this via its own registration)

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _open_config(self) -> None:
        ScanConfigDialog(parent=self).exec()

    # ------------------------------------------------------------------
    # CSV import – load a previous export to continue work
    # ------------------------------------------------------------------

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open AutoDoku Export",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        try:
            devices = import_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "Import Error", str(exc))
            logger.error("CSV import failed: %s", exc)
            return

        self._table.clear_devices()

        now = datetime.now(tz=timezone.utc).isoformat()
        self._session = ScanSession(
            ip_range="",
            created_at=now,
            name=f"Import {now[:10]}",
            devices=devices,
        )

        for device in devices:
            self._table.add_device(device)

        self._export_btn.setEnabled(bool(devices))
        self._update_stats()
        self._progress.set_progress(
            100,
            f"Imported {len(devices)} device(s) — ready to edit and export",
        )

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        devices = self._table.get_devices()
        if not devices:
            QMessageBox.information(self, "Export", "No data to export.")
            return

        # Sync live table state into session
        if self._session:
            self._session.devices = devices

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV File",
            "autodoku_export.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        try:
            if self._session is None:
                self._session = ScanSession(
                    ip_range="",
                    created_at=datetime.now(tz=timezone.utc).isoformat(),
                    name="Export",
                    devices=devices,
                )

            count = idoit_csv_exporter.export(self._session, path)
            QMessageBox.information(
                self,
                "Export Successful",
                f"✓  {count} row(s) exported to\n{path}",
            )
        except OSError as exc:
            QMessageBox.critical(self, "Export Error", str(exc))
            logger.error("CSV export failed: %s", exc)

    # ------------------------------------------------------------------
    # Window close
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(3000)
        event.accept()
