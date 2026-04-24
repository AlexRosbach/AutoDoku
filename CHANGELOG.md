# Changelog

All notable changes to AutoDoku are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — publish-readiness

### Changed
- License changed from MIT to GPL v3 (required by PyQt6 dependency)
- README: license badge updated, legal notice section added
- Added `.gitignore` (excludes `.venv/`, `build/`, `dist/`, `__pycache__/`)

---

## [1.2.1] — 2026-04-24

### Added
- **Peripheral Sysid field** — each peripheral now has its own i-doit Sysid field; populated on CSV re-import so i-doit updates the existing peripheral object instead of creating a duplicate
- **Peripheral suggestion indicator** — a visible "🟡 N suggestion" badge in the main table (new Peripherals column) shows at a glance that peripheral suggestions are waiting for review — no need to open the dialog
- **Peripheral suggestion banner** — when opening the Peripherals tab in the edit dialog, a prominent amber banner appears listing the number of unreviewed suggestions
- **Language switcher** — top-bar button toggles the entire UI between English (EN) and German (DE); column headers, button labels, stats bar and tooltips all update live
- **Scan method in Status column** — Status now shows the deep-scan protocol used: "✓ WMI", "✓ SSH", "✓ SNMP", or "✓ Basic" (port scan only) instead of just "✓ Done"

### Fixed
- **Column resize broken** — Hostname and OS columns were set to `Stretch` resize mode, preventing the user from resizing them; all columns now use interactive resize
- **App name darker background** — `QLabel#appTitle` now inherits the top-bar background correctly via `background: transparent` in QSS
- **German strings in Status column** — "Scannt…", "Fertig", "Fehler", "Ausstehend" replaced with English equivalents; scan progress messages in the progress bar are also translated

---

## [1.2.0] — 2026-04-24

### Added
- **In-memory architecture** — no SQLite database; all data lives only in the running process
- **CSV import** — reload a previous export to continue work without any local database (`⬆ Import CSV…`)
- **Monitor auto-suggestion** — desktop CLIENT devices automatically get a Monitor peripheral entry pre-filled; user only needs to add model and serial number
- **Laptop detection** — Monitor suggestion is suppressed for notebooks / laptops (detected via model name patterns: ThinkPad, Latitude, EliteBook, IdeaPad, MacBook, Surface, etc.)
- **CPU column** in the main result table
- **RAM column** in the main result table
- **New app logo** — magnifying glass with network nodes and document lines; dark background
- **App icon** in the taskbar and EXE file (multi-resolution ICO generated from SVG)
- **Version tracking** — `version.py`; version shown in window title
- **English UI** — all labels, tooltips, dialogs and messages are now in English
- **Issue templates** — Bug Report, Feature Request, Question / Support, Security
- **SECURITY.md** — vulnerability reporting policy
- **LICENSE** — MIT

### Changed
- Peripherals stored directly on `Device.peripherals` (in-memory list) instead of a separate SQLite table
- `idoit_csv_exporter`: uses human-readable `Objekt-Typ` labels (`Client`, `Server`, …) instead of i-doit internal constants; reads peripherals from `device.peripherals`; skips empty auto-suggestions
- `DeviceEditDialog`: removed `store` parameter; peripheral CRUD operates on `device.peripherals` directly
- UI colors moved from inline `setStyleSheet()` to QSS object names for consistency
- `result_table_widget`: removed `store.save_device()` call on inline cell edit
- Suggestion fields styled via QSS (`#suggestionField`, `#suggestionBadge`) instead of hardcoded Python strings
- README rewritten in English with download link, WMI setup guide, architecture overview

### Removed
- SQLite persistence from scan and UI paths (`SessionStore` no longer used at runtime)
- German UI strings
- Auto-load of last session on startup

---

## [1.1.0] — 2026-04-21

### Added
- **Multi-credential retry** for WMI, SSH and SNMP — all stored credentials tried in sequence; first success wins
- **WMI hard timeout** (20 s per attempt) via `concurrent.futures` — prevents DCOM hang from blocking subsequent credential sets
- **SSH deep scan** returns hostname, CPU, RAM, OS from Linux hosts (`hostname`, `lscpu`, `free -m`, `dmidecode`)
- **Two-phase device classification** — `classify()` on ports immediately; `reclassify_from_scan()` refines after OS string is known (Windows 10/11 → CLIENT, Windows Server → SERVER, Linux desktop → CLIENT)
- **Sysid field** — i-doit update key; when set on re-import, i-doit updates the existing object instead of creating a new one
- **Peripheral management** tab in `DeviceEditDialog` (Clients only)
- `PERIPHERAL_IDOIT_TYPE` mapping for correct i-doit object types in CSV export

### Fixed
- Only one device shown in table after multi-device scan (Qt sort race condition — `setSortingEnabled(False)` during row population)
- `_row_for()` returned wrong row after user sorts the table (switched from `_order.index()` to `_ROLE_DEVICE_ID` role scan)
- Double-click opening wrong device after sort
- RAM always 0 from WMI (`Win32_PhysicalMemoryArray.MaxCapacity` unreliable — switched to `TotalPhysicalMemory`)
- Manufacturer/Model showing "To be filled by O.E.M." (filter added for known OEM placeholders)

---

## [1.0.0] — 2026-04-18

### Initial release

- ARP network discovery via Windows `SendARP` API (no Npcap required)
- MAC vendor lookup via Wireshark OUI database (`manuf`, fully offline)
- TCP port scanner for device type classification
- Inline-editable result table with suggestion highlighting
- WMI deep scan (Windows hosts)
- SSH deep scan (Linux hosts)
- SNMP basic scan (switches, printers)
- Credentials stored in Windows Credential Manager (`keyring`)
- i-doit compatible CSV export (Sysid, all documentation fields, peripherals)
- Dark theme (Windows blue accent `#0078d4`)
- Portable single-file EXE (PyInstaller onefile, no installer required)
