"""Dialog for configuring scan credentials (WMI, SSH, SNMP)."""

import logging

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from data.credential_store import (
    SERVICE_SNMP,
    SERVICE_SSH,
    SERVICE_WMI,
    get_credentials,
    save_credentials,
)

logger = logging.getLogger(__name__)


class ScanConfigDialog(QDialog):
    """Tabbed dialog that stores WMI, SSH, and SNMP credentials via keyring."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scan-Konfiguration")
        self.setMinimumWidth(420)
        self._build_ui()
        self._load_credentials()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_wmi_tab(), "WMI (Windows)")
        tabs.addTab(self._build_ssh_tab(), "SSH (Linux)")
        tabs.addTab(self._build_snmp_tab(), "SNMP")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── WMI tab ──────────────────────────────────────────────────────

    def _build_wmi_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self._wmi_username = QLineEdit()
        self._wmi_username.setPlaceholderText("DOMAIN\\Administrator")
        self._wmi_password = QLineEdit()
        self._wmi_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(QLabel("Benutzername:"), self._wmi_username)
        form.addRow(QLabel("Passwort:"), self._wmi_password)
        return widget

    # ── SSH tab ──────────────────────────────────────────────────────

    def _build_ssh_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self._ssh_username = QLineEdit()
        self._ssh_username.setPlaceholderText("root")
        self._ssh_password = QLineEdit()
        self._ssh_password.setEchoMode(QLineEdit.EchoMode.Password)

        key_row = QWidget()
        key_layout = QFormLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        self._ssh_key_path = QLineEdit()
        self._ssh_key_path.setPlaceholderText("Pfad zum privaten Schlüssel (optional)")
        btn_browse = QPushButton("…")
        btn_browse.setFixedWidth(32)
        btn_browse.clicked.connect(self._browse_key)
        key_layout.addRow(self._ssh_key_path, btn_browse)

        form.addRow(QLabel("Benutzername:"), self._ssh_username)
        form.addRow(QLabel("Passwort:"), self._ssh_password)
        form.addRow(QLabel("Schlüsseldatei:"), key_row)
        return widget

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "SSH-Schlüsseldatei wählen", "", "Alle Dateien (*)"
        )
        if path:
            self._ssh_key_path.setText(path)

    # ── SNMP tab ─────────────────────────────────────────────────────

    def _build_snmp_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self._snmp_community = QLineEdit()
        self._snmp_community.setPlaceholderText("public")
        form.addRow(QLabel("Community String:"), self._snmp_community)
        return widget

    # ── Load / Save ──────────────────────────────────────────────────

    def _load_credentials(self) -> None:
        wmi = get_credentials(SERVICE_WMI)
        if wmi:
            self._wmi_username.setText(wmi[0])
            self._wmi_password.setText(wmi[1])

        ssh = get_credentials(SERVICE_SSH)
        if ssh:
            # Encode: username|key_path stored as username; password as password
            parts = ssh[0].split("|", 1)
            self._ssh_username.setText(parts[0])
            if len(parts) > 1:
                self._ssh_key_path.setText(parts[1])
            self._ssh_password.setText(ssh[1])

        snmp = get_credentials(SERVICE_SNMP)
        if snmp:
            self._snmp_community.setText(snmp[1])

    def _save_and_accept(self) -> None:
        # WMI
        wmi_user = self._wmi_username.text().strip()
        wmi_pass = self._wmi_password.text()
        if wmi_user:
            save_credentials(SERVICE_WMI, wmi_user, wmi_pass)

        # SSH — encode key path into the username field as "user|/path/to/key"
        ssh_user = self._ssh_username.text().strip()
        ssh_pass = self._ssh_password.text()
        ssh_key = self._ssh_key_path.text().strip()
        if ssh_user:
            username_key = f"{ssh_user}|{ssh_key}" if ssh_key else ssh_user
            save_credentials(SERVICE_SSH, username_key, ssh_pass)

        # SNMP — store community string as the password for a sentinel user
        snmp_community = self._snmp_community.text().strip() or "public"
        save_credentials(SERVICE_SNMP, "snmp", snmp_community)

        logger.info("Scan credentials saved")
        self.accept()
