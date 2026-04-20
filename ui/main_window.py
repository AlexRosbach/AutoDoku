"""AutoDoku main application window."""
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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.scanner import ScanWorker
from data.models import Device, ScanSession
from data.session_store import SessionStore
from export import idoit_csv_exporter
from ui.device_edit_dialog import DeviceEditDialog
from ui.device_tile_widget import DeviceTileWidget
from ui.export_review_dialog import ExportReviewDialog
from ui.progress_widget import ProgressWidget
from ui.result_table_widget import ResultTableWidget
from ui.scan_config_dialog import ScanConfigDialog

logger = logging.getLogger(__name__)

_VIEW_LIST = 0
_VIEW_TILE = 1


class MainWindow(QMainWindow):
    """Top-level window containing the scan controls, device views and export."""

    def __init__(self, config: dict) -> None:
        super().__init__()
        self._config  = config
        self._store   = SessionStore()
        self._session: ScanSession | None = None
        self._worker: ScanWorker | None = None
        self._view_mode = _VIEW_LIST

        self.setWindowTitle("AutoDoku – Netzwerkscanner")
        self.resize(1280, 780)
        self._build_ui()
        self._load_last_session()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_view_stack())
        root.addWidget(self._build_bottom_bar())

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        layout.addWidget(QLabel("IP-Bereich:"))
        self._ip_input = QLineEdit(self._config.get("default_ip_range", "192.168.1.0/24"))
        self._ip_input.setFixedWidth(200)
        layout.addWidget(self._ip_input)

        self._wmi_cb  = QCheckBox("WMI")
        self._wmi_cb.setToolTip("WMI-Scan für Windows-Hosts (Credentials erforderlich)")
        self._ssh_cb  = QCheckBox("SSH")
        self._ssh_cb.setToolTip("SSH-Scan für Linux-Hosts (Credentials erforderlich)")
        self._snmp_cb = QCheckBox("SNMP")
        self._snmp_cb.setToolTip("SNMP-Scan für Netzwerkgeräte")
        layout.addWidget(self._wmi_cb)
        layout.addWidget(self._ssh_cb)
        layout.addWidget(self._snmp_cb)

        layout.addStretch()

        # View toggle
        self._btn_list = QPushButton("☰ Liste")
        self._btn_list.setObjectName("btnSecondary")
        self._btn_list.setCheckable(True)
        self._btn_list.setChecked(True)
        self._btn_list.setFixedWidth(80)
        self._btn_list.clicked.connect(lambda: self._set_view(_VIEW_LIST))
        layout.addWidget(self._btn_list)

        self._btn_tile = QPushButton("⊞ Kacheln")
        self._btn_tile.setObjectName("btnSecondary")
        self._btn_tile.setCheckable(True)
        self._btn_tile.setFixedWidth(90)
        self._btn_tile.clicked.connect(lambda: self._set_view(_VIEW_TILE))
        layout.addWidget(self._btn_tile)

        self._config_btn = QPushButton("Konfigurieren")
        self._config_btn.setObjectName("btnSecondary")
        self._config_btn.clicked.connect(self._open_config)
        layout.addWidget(self._config_btn)

        self._scan_btn = QPushButton("Scan starten")
        self._scan_btn.clicked.connect(self._start_scan)
        layout.addWidget(self._scan_btn)

        self._stop_btn = QPushButton("Abbrechen")
        self._stop_btn.setObjectName("btnSecondary")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_scan)
        layout.addWidget(self._stop_btn)

        return bar

    def _build_view_stack(self) -> QStackedWidget:
        self._stack = QStackedWidget()

        self._table = ResultTableWidget()
        self._table.device_edit_requested.connect(self._open_device_edit)
        self._stack.addWidget(self._table)       # index 0 = LIST

        self._tiles = DeviceTileWidget()
        self._tiles.device_edit_requested.connect(self._open_device_edit)
        self._stack.addWidget(self._tiles)       # index 1 = TILE

        return self._stack

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._progress = ProgressWidget()
        self._progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._progress)

        self._export_btn = QPushButton("Exportieren (CSV)…")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_csv)
        layout.addWidget(self._export_btn)

        return bar

    # ------------------------------------------------------------------
    # View toggle
    # ------------------------------------------------------------------

    def _set_view(self, mode: int) -> None:
        self._view_mode = mode
        self._stack.setCurrentIndex(mode)
        self._btn_list.setChecked(mode == _VIEW_LIST)
        self._btn_tile.setChecked(mode == _VIEW_TILE)

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def _load_last_session(self) -> None:
        sessions = self._store.list_sessions()
        if not sessions:
            return
        last = self._store.load_session(sessions[-1].id)
        if last and last.devices:
            self._session = last
            self._ip_input.setText(last.ip_range)
            for device in last.devices:
                self._table.add_device(device)
                self._tiles.add_device(device)
            self._export_btn.setEnabled(True)
            self._progress.set_progress(
                100, f"Letzter Scan geladen: {len(last.devices)} Geräte"
            )

    # ------------------------------------------------------------------
    # Scan lifecycle
    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        ip_range = self._ip_input.text().strip()
        if not ip_range:
            QMessageBox.warning(self, "Fehler", "Bitte einen IP-Bereich eingeben.")
            return

        self._table.clear_devices()
        self._tiles.clear_devices()
        self._export_btn.setEnabled(False)
        self._progress.reset()

        now = datetime.now(tz=timezone.utc).isoformat()
        self._session = ScanSession(
            ip_range=ip_range,
            created_at=now,
            name=f"Scan {ip_range} – {now[:10]}",
        )
        self._store.save_session(self._session)

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
        self._tiles.add_device(device)

    def _on_scan_finished(self) -> None:
        self._scan_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        devices = self._table.get_devices()
        count = len(devices)
        if count > 0:
            self._export_btn.setEnabled(True)

        client_count = sum(
            1 for d in devices if d.device_type == "C__OBJTYPE__CLIENT"
        )
        if client_count:
            self._progress.set_progress(
                100,
                f"Scan abgeschlossen: {count} Gerät(e) — "
                f"{client_count} Client(s) erkannt. "
                "Doppelklick zum Bearbeiten / Monitore hinzufügen.",
            )
        else:
            self._progress.set_progress(
                100, f"Scan abgeschlossen: {count} Gerät(e) gefunden."
            )

    def _on_scan_error(self, message: str) -> None:
        self._scan_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Scan-Fehler", message)

    # ------------------------------------------------------------------
    # Device editing
    # ------------------------------------------------------------------

    def _open_device_edit(self, device: Device) -> None:
        dlg = DeviceEditDialog(device, self._store, parent=self)
        if dlg.exec() == DeviceEditDialog.DialogCode.Accepted:
            updated = dlg.apply()
            self._store.save_device(updated)
            self._table.update_device(updated)
            self._tiles.update_device(updated)
            if self._session:
                for i, d in enumerate(self._session.devices):
                    if d.id == updated.id:
                        self._session.devices[i] = updated
                        break

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _open_config(self) -> None:
        ScanConfigDialog(parent=self).exec()

    # ------------------------------------------------------------------
    # CSV export (with pre-export review dialog)
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        if not self._session or not self._session.devices:
            QMessageBox.information(self, "Export", "Keine Daten zum Exportieren.")
            return

        # Sync table devices into session
        self._session.devices = self._table.get_devices()

        # Show review dialog
        review = ExportReviewDialog(self._session.devices, parent=self)
        if review.exec() != ExportReviewDialog.DialogCode.Accepted:
            return

        reviewed_devices = review.get_devices()

        # Save any edits the user made in the review dialog
        for device in reviewed_devices:
            self._store.save_device(device)
            self._table.update_device(device)
            self._tiles.update_device(device)

        self._session.devices = reviewed_devices

        path, _ = QFileDialog.getSaveFileName(
            self,
            "CSV-Datei speichern",
            "autodoku_export.csv",
            "CSV-Dateien (*.csv);;Alle Dateien (*)",
        )
        if not path:
            return

        try:
            count = idoit_csv_exporter.export(self._session, path, self._store)
            QMessageBox.information(
                self,
                "Export erfolgreich",
                f"{count} Gerät(e) wurden nach\n{path}\nexportiert.",
            )
        except OSError as exc:
            QMessageBox.critical(self, "Export-Fehler", str(exc))
            logger.error("CSV export failed: %s", exc)

    # ------------------------------------------------------------------
    # Window close
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(3000)
        self._store.close()
        event.accept()
