"""Dialog for configuring scan credentials (WMI, SSH, SNMP).

Supports multiple credential sets per protocol so the scanner can try
them in sequence (e.g. different domain accounts or local admins).
"""
from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from data.credential_store import (
    SERVICE_SNMP,
    SERVICE_SSH,
    SERVICE_WMI,
    get_credentials_list,
    save_credentials_list,
)

logger = logging.getLogger(__name__)


class _CredentialListWidget(QWidget):
    """Reusable widget: a list of username/password pairs with Add/Remove."""

    def __init__(
        self,
        has_key_path: bool = False,
        placeholder_user: str = "Benutzername",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._has_key_path = has_key_path
        self._placeholder_user = placeholder_user
        self._creds: list[tuple[str, str]] = []   # (username_or_encoded, password)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._list = QListWidget()
        self._list.setFixedHeight(110)
        layout.addWidget(self._list)

        form_box = QGroupBox("Neue Zugangsdaten")
        form = QFormLayout(form_box)

        self._username = QLineEdit()
        self._username.setPlaceholderText(self._placeholder_user)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("Passwort")
        form.addRow(QLabel("Benutzer:"), self._username)
        form.addRow(QLabel("Passwort:"), self._password)

        if self._has_key_path:
            key_row = QWidget()
            key_layout = QHBoxLayout(key_row)
            key_layout.setContentsMargins(0, 0, 0, 0)
            self._key_path = QLineEdit()
            self._key_path.setPlaceholderText("Schlüsseldatei (optional)")
            btn_browse = QPushButton("…")
            btn_browse.setFixedWidth(32)
            btn_browse.clicked.connect(self._browse_key)
            key_layout.addWidget(self._key_path)
            key_layout.addWidget(btn_browse)
            form.addRow(QLabel("SSH-Schlüssel:"), key_row)
        else:
            self._key_path = None  # type: ignore[assignment]

        layout.addWidget(form_box)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_add = QPushButton("Hinzufügen")
        btn_add.clicked.connect(self._add_credential)
        btn_remove = QPushButton("Entfernen")
        btn_remove.setObjectName("btnSecondary")
        btn_remove.clicked.connect(self._remove_selected)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        layout.addWidget(btn_row)

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "SSH-Schlüsseldatei wählen", "", "Alle Dateien (*)"
        )
        if path and self._key_path:
            self._key_path.setText(path)

    def _add_credential(self) -> None:
        user = self._username.text().strip()
        password = self._password.text()
        if not user:
            return
        key = (self._key_path.text().strip() if self._key_path else "")
        encoded_user = f"{user}|{key}" if key else user
        self._creds.append((encoded_user, password))
        display = f"{user}  [{'***' if password else 'kein Passwort'}]"
        if key:
            display += f"  [Schlüssel: …{key[-20:]}]"
        self._list.addItem(QListWidgetItem(display))
        self._username.clear()
        self._password.clear()
        if self._key_path:
            self._key_path.clear()

    def _remove_selected(self) -> None:
        row = self._list.currentRow()
        if 0 <= row < len(self._creds):
            self._creds.pop(row)
            self._list.takeItem(row)

    # ── Public API ──────────────────────────────────────────────────────

    def load(self, creds: list[tuple[str, str]]) -> None:
        self._creds = list(creds)
        self._list.clear()
        for encoded_user, password in creds:
            user = encoded_user.split("|", 1)[0]
            display = f"{user}  [{'***' if password else 'kein Passwort'}]"
            self._list.addItem(QListWidgetItem(display))

    def get(self) -> list[tuple[str, str]]:
        return list(self._creds)


class ScanConfigDialog(QDialog):
    """Tabbed dialog that stores WMI, SSH, and SNMP credentials via keyring."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scan-Konfiguration")
        self.setMinimumWidth(460)
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
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_wmi_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel(
            "Mehrere Zugangsdaten werden der Reihe nach versucht."
        ))
        self._wmi_creds = _CredentialListWidget(
            placeholder_user="DOMAIN\\Administrator"
        )
        l.addWidget(self._wmi_creds)
        return w

    def _build_ssh_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel(
            "Mehrere Zugangsdaten werden der Reihe nach versucht."
        ))
        self._ssh_creds = _CredentialListWidget(
            has_key_path=True, placeholder_user="root"
        )
        l.addWidget(self._ssh_creds)
        return w

    def _build_snmp_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._snmp_community = QLineEdit()
        self._snmp_community.setPlaceholderText("public")
        form.addRow(QLabel("Community String:"), self._snmp_community)
        return w

    def _load_credentials(self) -> None:
        self._wmi_creds.load(get_credentials_list(SERVICE_WMI))
        self._ssh_creds.load(get_credentials_list(SERVICE_SSH))
        snmp = get_credentials_list(SERVICE_SNMP)
        if snmp:
            self._snmp_community.setText(snmp[0][1])

    def _save_and_accept(self) -> None:
        save_credentials_list(SERVICE_WMI, self._wmi_creds.get())
        save_credentials_list(SERVICE_SSH, self._ssh_creds.get())
        community = self._snmp_community.text().strip() or "public"
        save_credentials_list(SERVICE_SNMP, [("snmp", community)])
        logger.info("Scan credentials saved")
        self.accept()
