"""SQLite-backed persistence layer for scan sessions, devices and peripherals.

Auto-migrates the schema when new columns are added so existing databases
continue to work without manual intervention.
"""
from __future__ import annotations

import logging
import sqlite3
import sys
import threading
from pathlib import Path

from data.models import Device, Peripheral, ScanSession, ScanStatus

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    ip_range   TEXT NOT NULL,
    name       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    ip           TEXT,
    mac          TEXT,
    hostname     TEXT,
    device_type  TEXT,
    os           TEXT,
    manufacturer TEXT,
    model        TEXT,
    serial       TEXT,
    ram_gb       INTEGER,
    cpu          TEXT,
    cmdb_status  TEXT DEFAULT 'In Betrieb',
    location     TEXT,
    room         TEXT,
    department   TEXT,
    contact      TEXT,
    inventory_no TEXT,
    notes        TEXT,
    scan_status  TEXT,
    raw_data     TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS peripherals (
    id              TEXT PRIMARY KEY,
    device_id       TEXT NOT NULL,
    peripheral_type TEXT DEFAULT 'Monitor',
    manufacturer    TEXT,
    model           TEXT,
    serial          TEXT,
    notes           TEXT,
    FOREIGN KEY (device_id) REFERENCES devices(id)
);
"""

# Columns added after the initial schema – added via ALTER TABLE if missing
_DEVICE_MIGRATIONS: list[str] = [
    "cmdb_status  TEXT DEFAULT 'In Betrieb'",
    "room         TEXT DEFAULT ''",
    "contact      TEXT DEFAULT ''",
    "inventory_no TEXT DEFAULT ''",
]


def _get_db_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "autodoku.db"
    return Path(__file__).resolve().parent.parent / "autodoku.db"


class SessionStore:
    def __init__(self) -> None:
        self._db_path = _get_db_path()
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._migrate()
        logger.info("SessionStore at %s", self._db_path)

    def _init_db(self) -> None:
        with self._lock:
            self._conn.executescript(_DDL)
            self._conn.commit()

    def _migrate(self) -> None:
        """Add columns that may not exist in older databases."""
        for col_def in _DEVICE_MIGRATIONS:
            col_name = col_def.split()[0]
            try:
                self._conn.execute(f"ALTER TABLE devices ADD COLUMN {col_def}")
                self._conn.commit()
                logger.info("Migrated: added column '%s' to devices", col_name)
            except sqlite3.OperationalError:
                pass  # column already exists

        # Migrate monitors → peripherals (rename table if old name exists)
        try:
            self._conn.execute(
                "ALTER TABLE monitors RENAME TO peripherals"
            )
            self._conn.execute(
                "ALTER TABLE peripherals ADD COLUMN peripheral_type TEXT DEFAULT 'Monitor'"
            )
            self._conn.commit()
            logger.info("Migrated: renamed monitors → peripherals")
        except sqlite3.OperationalError:
            pass

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    def save_session(self, session: ScanSession) -> None:
        sql = "INSERT OR REPLACE INTO sessions (id, created_at, ip_range, name) VALUES (?,?,?,?)"
        with self._lock:
            self._conn.execute(sql, (session.id, session.created_at, session.ip_range, session.name))
            self._conn.commit()

    def load_session(self, session_id: str) -> ScanSession | None:
        row = self._conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            return None
        session = ScanSession(id=row["id"], created_at=row["created_at"],
                              ip_range=row["ip_range"], name=row["name"])
        session.devices = self.load_devices_for_session(session_id)
        return session

    def list_sessions(self) -> list[ScanSession]:
        rows = self._conn.execute("SELECT * FROM sessions ORDER BY created_at ASC").fetchall()
        return [ScanSession(id=r["id"], created_at=r["created_at"],
                            ip_range=r["ip_range"], name=r["name"]) for r in rows]

    # ------------------------------------------------------------------
    # Device CRUD
    # ------------------------------------------------------------------

    def save_device(self, device: Device) -> None:
        sql = """INSERT OR REPLACE INTO devices
            (id, session_id, ip, mac, hostname, device_type, os, manufacturer,
             model, serial, ram_gb, cpu, cmdb_status, location, room, department,
             contact, inventory_no, notes, scan_status, raw_data)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        with self._lock:
            self._conn.execute(sql, (
                device.id, device.session_id, device.ip, device.mac,
                device.hostname, device.device_type, device.os, device.manufacturer,
                device.model, device.serial, device.ram_gb, device.cpu,
                device.cmdb_status, device.location, device.room, device.department,
                device.contact, device.inventory_no, device.notes,
                device.scan_status, device.raw_data,
            ))
            self._conn.commit()

    def load_devices_for_session(self, session_id: str) -> list[Device]:
        rows = self._conn.execute(
            "SELECT * FROM devices WHERE session_id=?", (session_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = Device(
                id=r["id"], session_id=r["session_id"],
                ip=r["ip"] or "", mac=r["mac"] or "",
                hostname=r["hostname"] or "", device_type=r["device_type"] or "",
                os=r["os"] or "", manufacturer=r["manufacturer"] or "",
                model=r["model"] or "", serial=r["serial"] or "",
                ram_gb=r["ram_gb"], cpu=r["cpu"] or "",
                cmdb_status=r["cmdb_status"] or "",
                location=r["location"] or "", room=r["room"] or "",
                department=r["department"] or "", contact=r["contact"] or "",
                inventory_no=r["inventory_no"] or "", notes=r["notes"] or "",
                scan_status=r["scan_status"] or ScanStatus.DONE.value,
                raw_data=r["raw_data"] or "",
            )
            result.append(d)
        return result

    # ------------------------------------------------------------------
    # Peripheral CRUD
    # ------------------------------------------------------------------

    def save_peripheral(self, p: Peripheral) -> None:
        sql = """INSERT OR REPLACE INTO peripherals
            (id, device_id, peripheral_type, manufacturer, model, serial, notes)
            VALUES (?,?,?,?,?,?,?)"""
        with self._lock:
            self._conn.execute(sql, (
                p.id, p.device_id, p.peripheral_type,
                p.manufacturer, p.model, p.serial, p.notes,
            ))
            self._conn.commit()

    def load_peripherals_for_device(self, device_id: str) -> list[Peripheral]:
        rows = self._conn.execute(
            "SELECT * FROM peripherals WHERE device_id=?", (device_id,)
        ).fetchall()
        return [Peripheral(
            id=r["id"], device_id=r["device_id"],
            peripheral_type=r["peripheral_type"] or "Monitor",
            manufacturer=r["manufacturer"] or "", model=r["model"] or "",
            serial=r["serial"] or "", notes=r["notes"] or "",
        ) for r in rows]

    def delete_peripheral(self, peripheral_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM peripherals WHERE id=?", (peripheral_id,))
            self._conn.commit()

    def count_peripherals(self, device_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM peripherals WHERE device_id=?", (device_id,)
        ).fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()
