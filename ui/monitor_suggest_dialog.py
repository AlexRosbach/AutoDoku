"""Dialog for entering monitor details to attach to a CLIENT device."""

import logging

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from data.models import Monitor

logger = logging.getLogger(__name__)


class MonitorSuggestDialog(QDialog):
    """Modal dialog that collects manufacturer, model and serial for a monitor.

    Call :meth:`get_monitor` after ``exec()`` returns ``Accepted`` to retrieve
    the populated Monitor dataclass.
    """

    def __init__(self, device_id: str, parent=None) -> None:
        super().__init__(parent)
        self._device_id = device_id
        self.setWindowTitle("Monitor hinzufügen")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._manufacturer = QLineEdit()
        self._manufacturer.setPlaceholderText("z.B. Dell, HP, LG …")

        self._model = QLineEdit()
        self._model.setPlaceholderText("z.B. U2722D")

        self._serial = QLineEdit()
        self._serial.setPlaceholderText("Seriennummer")

        self._notes = QLineEdit()
        self._notes.setPlaceholderText("Optionale Notizen")

        form = QFormLayout()
        form.addRow(QLabel("Hersteller:"), self._manufacturer)
        form.addRow(QLabel("Modell:"), self._model)
        form.addRow(QLabel("Seriennummer:"), self._serial)
        form.addRow(QLabel("Notizen:"), self._notes)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_monitor(self) -> Monitor:
        """Return a Monitor populated from the form fields."""
        return Monitor(
            device_id=self._device_id,
            manufacturer=self._manufacturer.text().strip(),
            model=self._model.text().strip(),
            serial=self._serial.text().strip(),
            notes=self._notes.text().strip(),
        )
