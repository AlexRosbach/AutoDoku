<div align="center">

<img src="ui/assets/autodoku.svg" alt="AutoDoku Logo" width="110" height="110" />

# AutoDoku

**Network Scanner & i-doit Documentation Assistant for Windows**

[![Version](https://img.shields.io/badge/version-1.2.3-0078d4)](https://github.com/AlexRosbach/AutoDoku/releases/latest)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-22c55e)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078d4)](https://github.com/AlexRosbach/AutoDoku)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab)](https://python.org)

AutoDoku scans your network, automatically identifies devices, and helps you fill in all the fields needed for an i-doit import — with smart auto-suggestions, inline editing, and peripheral management. No database, no server, no install.

[**⬇ Download AutoDoku.exe**](https://github.com/AlexRosbach/AutoDoku/releases/latest)

</div>

---

## Features

- **Network discovery** via Windows `SendARP` API — no Npcap, no nmap, no elevated privileges required
- **MAC vendor lookup** offline via Wireshark OUI database (`manuf`)
- **Automatic device classification** by port, vendor and hostname; refined by OS string after deep scan
- **Windows 10/11 → Client**, **Windows Server → Server**, **Linux desktop → Client** out of the box
- **Deep scan via WMI** (Windows) — reads CPU, RAM, OS, model, serial number
- **Deep scan via SSH** (Linux) — reads hostname, CPU, RAM, OS, model
- **SNMP basic scan** (switches, printers, routers)
- **Multi-credential support** — multiple credential sets per protocol tried in order; WMI attempts have a hard 20-second timeout so a hanging DCOM connection never blocks the next set
- **Monitor auto-suggestion** — when a desktop Client is found, AutoDoku pre-fills a Monitor peripheral; user only needs to add model and serial number. Laptops are detected and skipped automatically.
- **Inline-editable result table** — CPU, RAM, model, serial and all documentation fields visible and editable directly in the table
- **Auto-suggestions** highlighted in amber — CMDB status, location, room, department, OS and more
- **Full i-doit field set** — Inventory No., CMDB Status, Location, Room, Department, Contact, Sysid
- **Sysid field** — on CSV re-import i-doit updates the existing object instead of creating a duplicate
- **Peripheral management** per Client (Monitor, Keyboard, Mouse, Headset, Docking Station, VoIP, Printer, Webcam, …)
- **CSV export** in i-doit-compatible format — devices and peripherals as consecutive rows in one file
- **Export selection** — tick devices on/off before export; excluded devices and their peripherals stay visible but are omitted from the CSV
- **CSV import** — reload a previous export to continue documenting without any local database
- **Fully in-memory** — nothing is written to disk until you export; the CSV is the only persistence
- **Documentation score** per device with progress bar and suggestion counter
- **Stats bar** — live device count by type (Clients, Servers, Switches, …)
- **Portable EXE** — no install, no Python, no dependencies; just run

---

## Download

| | |
|---|---|
| **Latest release** | [AutoDoku.exe — v1.2.3](https://github.com/AlexRosbach/AutoDoku/releases/latest) |
| **All releases** | [github.com/AlexRosbach/AutoDoku/releases](https://github.com/AlexRosbach/AutoDoku/releases) |

Just download `AutoDoku.exe` and run it — no installer, no Python, no Npcap required.

---

## Quick Start (from source)

**Requirements:** Python 3.11+, Windows

```bash
git clone https://github.com/AlexRosbach/AutoDoku.git
cd AutoDoku
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Build the EXE yourself

```bat
build.bat
```

The script creates a virtual environment, installs dependencies, generates the app icon, and runs PyInstaller. The finished `AutoDoku.exe` is placed in `dist\`.

---

## Usage

### 1. Scan

Enter an IP range (e.g. `192.168.1.0/24`) and click **▶ Start Scan**.  
Devices appear in the table as they are discovered:

| Badge | Meaning |
|---|---|
| ⟳ Scanning… | Deep scan in progress |
| ✓ Done | Host fully scanned |
| ✗ Error | Host unreachable or deep scan failed |
| … Pending | Not yet reached |

Optional deep-scan modules:

| Module | Purpose | Requirement |
|---|---|---|
| **WMI** | Hardware details from Windows hosts | Store credentials + WMI enabled on target |
| **SSH** | Hardware details from Linux hosts | Store credentials or SSH key |
| **SNMP** | Basic info from switches, printers | Configure community string |

---

### 2. Edit data

Every cell in the table is editable directly.

| Cell colour | Meaning |
|---|---|
| 🟡 **Amber / italic** | Auto-suggestion — review and adjust if needed |
| ⬜ **Normal** | Manually entered or confirmed value |
| ⬛ **Dark grey** | Read-only scan result |

**Double-click** any row to open the full edit dialog with three tabs:

- **🔍 Scan Result** — all detected hardware details at a glance
- **📋 Documentation** — all i-doit fields including Sysid and completion score
- **🖱 Peripherals** *(Clients only)* — manage attached devices; auto-suggested peripherals shown in amber

---

### 3. Store credentials

Click **⚙ Configure** to add credentials for each protocol.  
AutoDoku tries them in order and stops at the first successful authentication.

| Protocol | Format |
|---|---|
| WMI | `DOMAIN\user` or `.\user` + password |
| SSH (password) | `user` + password |
| SSH (key) | `user\|/path/to/key` (pipe separates username and key path) |
| SNMP | Community string (e.g. `public`) |

Credentials are stored in the **Windows Credential Manager** (encrypted).

---

### 4. Export CSV

Click **⬇ Export as CSV…** to generate an i-doit-compatible CSV file:

- Use the **Export** checkbox column to decide which devices are included
- Each device = one row with a human-readable `Object Type` (`Client`, `Server`, …)
- Peripherals follow immediately after their parent device row
- If a device is unchecked, its peripherals are skipped as well
- **Sysid column first** — when populated, i-doit updates the existing object on import
- Auto-suggested peripherals without a model or serial are silently skipped

**Import into i-doit:** *Extras → Import → CSV Import*

---

### 5. Import CSV (resume work)

Click **⬆ Import CSV…** to reload a previous AutoDoku export:

- All devices and peripheral objects are reconstructed in memory
- Sysids are preserved — the next export will update existing i-doit objects
- AutoDoku stores **nothing locally** — the export file is the only persistence

---

## i-doit Workflow

```
First scan (Sysid empty)
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│ AutoDoku scans  │────▶│ Export CSV       │────▶│ i-doit Import          │
│ network         │     │ Sysid column     │     │ → creates new objects  │
└─────────────────┘     │ left blank       │     └──────────┬─────────────┘
                        └──────────────────┘               │
                                                 i-doit assigns Sysids
                                                           │
Follow-up scan (Sysid filled)                              ▼
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│ Import previous │────▶│ New scan or      │────▶│ i-doit Import          │
│ CSV export      │     │ manual edits     │     │ → updates objects      │
└─────────────────┘     │ → Export CSV     │     └────────────────────────┘
                        └──────────────────┘
```

---

## WMI Deep Scan Setup

The following steps need to be performed on each **target Windows PC**.

### Step 1 — Enable the WMI service

```powershell
# Run as Administrator
Set-Service -Name winmgmt -StartupType Automatic
Start-Service winmgmt
```

### Step 2 — Open firewall rules

```powershell
# DCOM port 135
netsh advfirewall firewall add rule `
  name="AutoDoku WMI DCOM" `
  dir=in action=allow protocol=TCP localport=135

# WMI dynamic ports (predefined rule group)
Enable-NetFirewallRule -DisplayGroup "Windows Management Instrumentation (WMI)"
```

### Step 3 — Add scan account to DCOM Users

```powershell
# Domain account (recommended)
Add-LocalGroupMember -Group "Distributed COM Users" -Member "DOMAIN\ScanUser"

# Or use a local administrator account (simpler, broader access)
Add-LocalGroupMember -Group "Administrators" -Member "ScanUser"
```

### Step 4 — WMI namespace permissions (non-admin accounts only)

If the scan account is **not** a local administrator:

1. Open `wmimgmt.msc`
2. Right-click **WMI Control (Local)** → **Properties**
3. **Security** tab → select `Root\CIMV2` → click **Security**
4. Add the account and grant **Enable Account** + **Remote Enable**

### Step 5 — UAC remote access (local accounts only)

Required when using a local (non-domain) account:

```powershell
# Disables UAC token filtering for remote access — affects all local accounts
New-ItemProperty `
  -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" `
  -Name LocalAccountTokenFilterPolicy -Value 1 -PropertyType DWORD -Force
```

> **Note:** In domain environments, use a domain account with appropriate permissions instead.

### Step 6 — Store credentials in AutoDoku

Open AutoDoku → **⚙ Configure** → add WMI credentials:

- **Username:** `DOMAIN\ScanUser` or `.\local_admin`
- **Password:** account password

AutoDoku tries all stored credential sets in order and stops at the first success.  
Each attempt has a **20-second timeout** so a stalled DCOM handshake never freezes the scan.

---

## Configuration

`config.json` sits next to `AutoDoku.exe` and can be edited with any text editor:

| Key | Default | Description |
|---|---|---|
| `default_ip_range` | `192.168.1.0/24` | Pre-filled IP range in the UI |
| `scan_timeout` | `2` | Timeout in seconds per host (ARP + ports) |
| `max_threads` | `50` | Maximum parallel scan threads |
| `default_ports` | `[22, 80, 135, 161, 443, 3389, 9100]` | Ports used for device type classification |
| `snmp_community` | `public` | Default SNMP community string |
| `log_level` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`) |
| `mock_mode` | `false` | Demo mode — generates fake devices without a real scan |

The log file (`autodoku.log`) is written next to the EXE. No database is created.

---

## Architecture

```
AutoDoku/
├── main.py                    # Entry point: logging, stylesheet, app icon
├── version.py                 # Version constants (__version__, __app_name__)
├── config.json                # Runtime configuration
├── core/
│   ├── arp_sweep.py           # Windows SendARP host discovery (no Npcap)
│   ├── scanner.py             # Scan worker (QThread): ARP → ports → WMI/SSH/SNMP
│   ├── device_classifier.py   # Port/vendor/OS classification + laptop detection
│   ├── suggestions.py         # Proactive field suggestions
│   ├── vendor_lookup.py       # MAC vendor via manuf (Wireshark OUI, offline)
│   ├── port_scanner.py        # TCP connect port scanner (no nmap)
│   ├── wmi_connector.py       # WMI deep scan with 20s hard timeout
│   ├── ssh_connector.py       # SSH deep scan (hostname, CPU, RAM, OS, serial)
│   └── snmp_connector.py      # SNMP basic scan
├── data/
│   ├── models.py              # Device, Peripheral, ScanSession dataclasses
│   └── credential_store.py    # Windows Credential Manager (keyring)
├── export/
│   ├── idoit_csv_exporter.py  # i-doit CSV export (human-readable types, peripherals)
│   └── csv_importer.py        # AutoDoku CSV re-import → list[Device]
├── tools/
│   └── make_ico.py            # Generates autodoku.ico from SVG (used by build.bat)
└── ui/
    ├── main_window.py         # Main window: scan controls, stats bar, import/export
    ├── result_table_widget.py # Inline-editable device table with suggestion highlighting
    ├── device_edit_dialog.py  # 3-tab dialog: Scan Result / Documentation / Peripherals
    ├── peripheral_dialog.py   # Add / edit peripheral
    ├── scan_config_dialog.py  # Credential management
    ├── progress_widget.py     # Progress bar
    ├── styles/dark_theme.qss  # Dark theme (accent: #0078d4)
    └── assets/
        ├── autodoku.svg       # Vector logo
        └── autodoku.ico       # App icon (multi-resolution, generated from SVG)
```

**Stack:**

| Layer | Technology |
|---|---|
| GUI | PyQt6 |
| Persistence | CSV file (no server, no database) |
| Network discovery | Windows `SendARP` via ctypes — no Npcap |
| Deep scan | WMI (`wmi`), SSH (`paramiko`), SNMP (`pysnmp`) |
| MAC vendor lookup | `manuf` (Wireshark OUI database, fully offline) |
| Credential storage | Windows Credential Manager (`keyring`) |
| Build | PyInstaller 6.x (one-file portable EXE) |

---

## System Requirements

| Requirement | Details |
|---|---|
| **OS** | Windows 10 / 11 (64-bit) |
| **Network** | Must be on the same Layer-2 segment as the scanned hosts |
| **Privileges** | Standard user for ARP scan; WMI/SSH require valid target credentials |
| **Npcap / nmap** | **Not required** |
| **Python** | 3.11+ only needed to run from source or build the EXE |

---

## Legal Notice

This tool is intended for use **only on networks you own or have explicit written permission to scan**.
Unauthorized network scanning may violate applicable laws (e.g. German StGB § 202c).
The author assumes no liability for misuse.

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).

AutoDoku uses [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) which is licensed under GPL v3.
As a result, AutoDoku is also distributed under GPL v3.

---

## Contributing

Bug reports, feature requests and questions are welcome via [GitHub Issues](https://github.com/AlexRosbach/AutoDoku/issues).

---

<div align="center">

Built for IT teams running i-doit who want to speed up initial device cataloguing.

</div>
