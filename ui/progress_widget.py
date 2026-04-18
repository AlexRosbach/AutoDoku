"""Progress bar widget with a text status label beneath it."""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class ProgressWidget(QWidget):
    """Combines a QProgressBar with a status label.

    Usage::

        widget = ProgressWidget(parent)
        widget.set_progress(50, "Scanning 5/10 hosts…")
        widget.reset()
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)

        self._label = QLabel("Bereit.")
        self._label.setObjectName("statusLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._bar)
        layout.addWidget(self._label)

    def set_progress(self, value: int, message: str) -> None:
        """Update the progress bar to *value* (0–100) and display *message*."""
        self._bar.setValue(max(0, min(100, value)))
        self._label.setText(message)

    def reset(self) -> None:
        """Reset bar to zero and clear the status message."""
        self._bar.setValue(0)
        self._label.setText("Bereit.")
