"""SQLite-backed persistence layer for scan sessions, devices and monitors.

Uses a single connection with check_same_thread=False and a threading.Lock so
that ScanWorker background threads can safely call save_device() concurrently.

The database file (autodoku.db) is placed next to the EXE when running as a
PyInstaller bundle, or at the project root when running as plain Python.
"""
from __future__ import annotations
import json
import logging
import sqlite3
import sys
import threading
from pathlib import Path

from data.models import Device, Monitor, ScanSession, ScanStatus

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    ip_range   TEXT NOT NULL,
    name       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    ip          TEXT,
    mac         TEXT,
    hostname    TEXT,
    device_type TEXT,
    os          TEXT,
    manufacturer TEXT,
    model       TEXT,
    serial      TEXT,
    ram_gb      INTEGER,
    cpu         TEXT,
    location    TEXT,
    department  TEXT,
    notes       TEXT,
    scan_status TEXT,
    raw_data    TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS monitors (
    id           TEXT PRIMARY KEY,
    device_id    TEXT NOT NULL,
    manufacturer TEXT,
    model        TEXT,
    serial       TEXT,
    notes        TEXT,
    FOREIGN KEY (device_id) REFERENCES devices(id)
);
"""


def _get_db_path() -> Path:
    """Return the path to autodoku.db, portable across frozen and script modes."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "autodoku.db"
    return Path(__file__).resolve().parent.parent / "autodoku.db"


class SessionStore:
    """Provides CRUD operations for ScanSession, Device and Monitor records."""

    def __init__(self) -> None:
        self._db_path = _get_db_path()
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self._db_path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        logger.info("SessionStore initialised at %s", self._db_path)

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._lock:
            self._conn.executescript(_DDL)
            self._conn.commit()

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    def save_session(self, session: ScanSession) -> None:
        """Insert or replace a ScanSession record (without its devices)."""
        sql = """
            INSERT OR REPLACE INTO sessions (id, created_at, ip_range, name)
            VALUES (?, ?, ?, ?)
        """
        with self._lock:
            self._conn.execute(
                sql, (session.id, session.created_at, session.ip_range, session.name)
            )
            self._conn.commit()

    def load_session(self, session_id: str) -> ScanSession | None:
        """Load a ScanSession and all its devices (without monitors) by ID."""
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        session = ScanSession(
            id=row["id"],
            created_at=row["created_at"],
            ip_range=row["ip_range"],
            name=row["name"],
        )
        session.devices = self.load_devices_for_session(session_id)
        return session

    def list_sessions(self) -> list[ScanSession]:
        """Return all sessions ordered by creation time (oldest first)."""
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY created_at ASC"
        ).fetchall()
        return [
            ScanSession(
                id=r["id"],
                created_at=r["created_at"],
                ip_range=r["ip_range"],
                name=r["name"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Device CRUD
    # ------------------------------------------------------------------

    def save_device(self, device: Device) -> None:
        """Insert or replace a Device record."""
        sql = """
            INSERT OR REPLACE INTO devices
            (id, session_id, ip, mac, hostname, device_type, os, manufacturer,
             model, serial, ram_gb, cpu, location, department, notes,
             scan_status, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._lock:
            self._conn.execute(
                sql,
                (
                    device.id, device.session_id, device.ip, device.mac,
                    device.hostname, device.device_type, device.os,
                    device.manufacturer, device.model, device.serial,
                    device.ram_gb, device.cpu, device.location,
                    device.department, device.notes, device.scan_status,
                    device.raw_data,
                ),
            )
            self._conn.commit()

    def load_devices_for_session(self, session_id: str) -> list[Device]:
        """Return all devices belonging to the given session."""
        rows = self._conn.execute(
            "SELECT * FROM devices WHERE session_id = ?", (session_id,)
        ).fetchall()
        devices = []
        for r in rows:
            d = Device(
                id=r["id"],
                session_id=r["session_id"],
                ip=r["ip"] or "",
                mac=r["mac"] or "",
                hostname=r["hostname"] or "",
                device_type=r["device_type"] or "",
                os=r["os"] or "",
                manufacturer=r["manufacturer"] or "",
                model=r["model"] or "",
                serial=r["serial"] or "",
                ram_gb=r["ram_gb"],
                cpu=r["cpu"] or "",
                location=r["location"] or "",
                department=r["department"] or "",
                notes=r["notes"] or "",
                scan_status=r["scan_status"] or ScanStatus.DONE.value,
                raw_data=r["raw_data"] or "",
            )
            devices.append(d)
        return devices

    # ------------------------------------------------------------------
    # Monitor CRUD
    # ------------------------------------------------------------------

    def save_monitor(self, monitor: Monitor) -> None:
        """Insert or replace a Monitor record."""
        sql = """
            INSERT OR REPLACE INTO monitors
            (id, device_id, manufacturer, model, serial, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with self._lock:
            self._conn.execute(
                sql,
                (
                    monitor.id, monitor.device_id, monitor.manufacturer,
                    monitor.model, monitor.serial, monitor.notes,
                ),
            )
            self._conn.commit()

    def load_monitors_for_device(self, device_id: str) -> list[Monitor]:
        """Return all monitors associated with the given device."""
        rows = self._conn.execute(
            "SELECT * FROM monitors WHERE device_id = ?", (device_id,)
        ).fetchall()
        return [
            Monitor(
                id=r["id"],
                device_id=r["device_id"],
                manufacturer=r["manufacturer"] or "",
                model=r["model"] or "",
                serial=r["serial"] or "",
                notes=r["notes"] or "",
            )
            for r in rows
        ]

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            self._conn.close()
