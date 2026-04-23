"""AutoDoku application entry point.

Sets up logging, loads config and the dark-mode stylesheet, then launches the
PyQt6 main window.  Works both as a plain Python script and as a PyInstaller
one-file bundle (sys.frozen / sys._MEIPASS detection ensures correct paths).
"""

import json
import logging
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from version import __version__, __app_name__

# ---------------------------------------------------------------------------
# Path helpers (frozen-EXE-aware)
# ---------------------------------------------------------------------------

def _base_dir() -> Path:
    """Directory next to the EXE (or project root in dev mode).

    Used for user-writable files: autodoku.log, autodoku.db, config.json
    override.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def _resource_dir() -> Path:
    """Directory containing bundled read-only assets (QSS, default config).

    In a PyInstaller onefile bundle, assets are extracted to sys._MEIPASS.
    In dev mode this is the same as _base_dir().
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Bootstrap helpers
# ---------------------------------------------------------------------------

def _setup_logging(level: str = "INFO") -> None:
    log_path = _base_dir() / "autodoku.log"
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(str(log_path), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("paramiko").setLevel(logging.WARNING)


def _load_config() -> dict:
    defaults: dict = {
        "default_ip_range": "192.168.1.0/24",
        "scan_timeout": 2,
        "max_threads": 50,
        "default_ports": [22, 80, 135, 161, 443, 3389, 9100],
        "snmp_community": "public",
        "log_level": "INFO",
        "mock_mode": False,
    }
    # Try user-editable override next to EXE first, then bundled default.
    candidates = [_base_dir() / "config.json", _resource_dir() / "config.json"]
    for config_path in candidates:
        try:
            with config_path.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
                defaults.update(loaded)
                return defaults
        except FileNotFoundError:
            continue
        except json.JSONDecodeError as exc:
            logging.warning("config.json is malformed (%s) – using defaults", exc)
            return defaults
    logging.warning("config.json not found – using defaults")
    return defaults


def _load_stylesheet() -> str:
    qss_path = _resource_dir() / "ui" / "styles" / "dark_theme.qss"
    try:
        return qss_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logging.warning("dark_theme.qss not found – running without stylesheet")
        return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    config = _load_config()
    _setup_logging(config.get("log_level", "INFO"))

    logger = logging.getLogger(__name__)
    logger.info("%s %s starting (Python %s)", __app_name__, __version__, sys.version.split()[0])

    app = QApplication(sys.argv)
    app.setApplicationName("AutoDoku")
    app.setOrganizationName("AutoDoku")

    # App icon (SVG works on all platforms via Qt's SVG support)
    icon_path = _resource_dir() / "ui" / "assets" / "autodoku.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
