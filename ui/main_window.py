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
    QVBoxLayout,
    QWidget,
)

from core.scanner import ScanWorker
from data.models import Device, ScanSession
from data.session_store import SessionStore
from export import idoit_csv_exporter
from ui.device_edit_dialog import DeviceEditDialog
from ui.progress_widget import ProgressWidget
from ui.result_table_widget import ResultTableWidget
from ui.scan_config_dialog import ScanConfigDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Top-level window containing the scan controls, device table and export."""

    def __init__(self, config: dict) -> None:
        super().__init__()
        self._config = config
        self._store = SessionStore()
        self._session: ScanSession | None = None
        self._worker: ScanWorker | None = None

        self.setWindowTitle("AutoDoku – Netzwerkscanner")
        self.resize(1280, 760)
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
        root.addWidget(self._build_table())
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

        # Deep-scan checkboxes
        self._wmi_cb = QCheckBox("WMI")
        self._wmi_cb.setToolTip("WMI-Scan für Windows-Hosts (Credentials erforderlich)")
        self._ssh_cb = QCheckBox("SSH")
        self._ssh_cb.setToolTip("SSH-Scan für Linux-Hosts (Credentials erforderlich)")
        self._snmp_cb = QCheckBox("SNMP")
        self._snmp_cb.setToolTip("SNMP-Scan für Netzwerkgeräte")
        layout.addWidget(self._wmi_cb)
        layout.addWidget(self._ssh_cb)
        layout.addWidget(self._snmp_cb)

        layout.addStretch()

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

    def _build_table(self) -> QWidget:
        self._table = ResultTableWidget()
        self._table.device_edit_requested.connect(self._open_device_edit)
        return self._table

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._progress = ProgressWidget()
        self._progress.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self._progress)

        self._export_btn = QPushButton("Exportieren (CSV)")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_csv)
        layout.addWidget(self._export_btn)

        return bar

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
            self._export_btn.setEnabled(True)
            self._progress.set_progress(
                100, f"Letzter Scan geladen: {len(last.devices)} Geräte"
            )
            logger.info("Loaded previous session with %d devices", len(last.devices))

    # ------------------------------------------------------------------
    # Scan lifecycle
    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        ip_range = self._ip_input.text().strip()
        if not ip_range:
            QMessageBox.warning(self, "Fehler", "Bitte einen IP-Bereich eingeben.")
            return

        self._table.clear_devices()
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
        logger.info("Scan started for range %s", ip_range)

    def _stop_scan(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._stop_btn.setEnabled(False)
            self._progress.set_progress(self._progress._bar.value(), "Abbrechen…")

    def _on_device_found(self, device: Device) -> None:
        self._table.add_device(device)

    def _on_scan_finished(self) -> None:
        self._scan_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        count = len(self._table.get_devices())
        if count > 0:
            self._export_btn.setEnabled(True)
        logger.info("Scan finished, %d devices in table", count)

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

            # Sync back into the in-memory session
            if self._session:
                for i, d in enumerate(self._session.devices):
                    if d.id == updated.id:
                        self._session.devices[i] = updated
                        break

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _open_config(self) -> None:
        dlg = ScanConfigDialog(parent=self)
        dlg.exec()

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        if not self._session or not self._session.devices:
            QMessageBox.information(self, "Export", "Keine Daten zum Exportieren vorhanden.")
            return

        # Sync table devices into session before export
        self._session.devices = self._table.get_devices()

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
            logger.info("CSV export complete: %d rows to %s", count, path)
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
