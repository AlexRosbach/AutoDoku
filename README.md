<div align="center">

<img src="ui/assets/autodoku.svg" alt="AutoDoku Logo" width="80" height="80" />

# AutoDoku

**Netzwerkscanner & i-doit Dokumentationsassistent für Windows**

[![Version](https://img.shields.io/badge/version-1.0.0-0078d4)](https://github.com/AlexRosbach/AutoDoku)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-0078d4)](https://github.com/AlexRosbach/AutoDoku)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab)](https://python.org)

AutoDoku scannt dein Netzwerk, erkennt Geräte automatisch und hilft dir, alle relevanten Felder für den i-doit-Import auszufüllen — mit proaktiven Vorschlägen, Inline-Bearbeitung und Peripherie-Verwaltung.

</div>

---

## Features

- **Netzwerk-Discovery** via Windows `SendARP` API — kein Npcap, kein nmap, keine erhöhten Rechte nötig
- **MAC-Vendor-Lookup** offline via Wireshark OUI-Datenbank (`manuf`)
- **Automatische Geräteklassifikation** nach Hersteller, Hostname-Muster und offenen Ports
- **Deep Scan** via WMI (Windows), SSH (Linux) und SNMP — liest CPU, RAM, OS, Modell, Seriennummer
- **Multi-Credential-Support** — mehrere Zugangsdaten pro Protokoll, werden der Reihe nach probiert
- **Inline-editierbare Scan-Tabelle** — das Arbeitsdokument direkt im Scanner, kein separater Bearbeitungsschritt
- **Proaktive Feld-Vorschläge** (gelb markiert) für CMDB-Status, Standort, Raum, Abteilung, OS, Hostname uvm.
- **Vollständige i-doit-Felder** — Inventarnummer, CMDB-Status, Standort, Raum, Abteilung, Ansprechpartner, Sysid
- **Sysid-Feld** — beim CSV-Reimport werden bestehende i-doit-Objekte aktualisiert statt dupliziert
- **Peripherie-Verwaltung** pro Client — Monitor, Tastatur, Maus, Headset, Docking Station, VoIP, Drucker, Webcam uvm.
- **CSV-Export** im i-doit-kompatiblen Format — Geräte und Peripherie als separate Zeilen in einer Datei
- **Dokumentationsgrad-Anzeige** pro Gerät mit Fortschrittsbalken und Vorschlag-Zähler
- **Stats-Bar** — Live-Übersicht der Gerätanzahl nach Typ (Clients, Server, Switches, …)
- **Portables EXE** — keine Installation, kein Python, keine Abhängigkeiten; einfach starten

---

## Quick Start

### Variante A — Portable EXE *(empfohlen)*

1. [**AutoDoku.exe herunterladen**](https://github.com/AlexRosbach/AutoDoku/releases/latest)
2. Doppelklick auf `AutoDoku.exe`
3. IP-Bereich eingeben und **▶ Scan starten** klicken

Keine Installation, kein Python, kein Npcap erforderlich.

---

### Variante B — Aus dem Quellcode starten

**Voraussetzungen:** Python 3.11+, Windows

```bash
git clone https://github.com/AlexRosbach/AutoDoku.git
cd AutoDoku
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

### Variante C — EXE selbst bauen

```bat
build.bat
```

Das Skript erstellt automatisch eine virtuelle Umgebung, installiert alle Abhängigkeiten und ruft PyInstaller auf. Die fertige `AutoDoku.exe` liegt danach unter `dist\`.

---

## Bedienung

### 1. Scan

IP-Bereich eingeben (z. B. `192.168.1.0/24`) und auf **▶ Scan starten** klicken.  
Gefundene Geräte erscheinen sofort in der Tabelle mit Scan-Status-Badge:

| Badge | Bedeutung |
|---|---|
| ⟳ Scannt… | Deep Scan läuft gerade |
| ✓ Fertig | Host vollständig gescannt |
| ✗ Fehler | Host nicht erreichbar / Deep Scan fehlgeschlagen |
| … Ausstehend | Noch nicht erreicht |

Optionale Deep-Scan-Module:

| Modul | Zweck | Voraussetzung |
|---|---|---|
| **WMI** | Hardware-Details von Windows-Hosts | Zugangsdaten hinterlegen |
| **SSH** | Hardware-Details von Linux-Hosts | Zugangsdaten oder SSH-Key |
| **SNMP** | Basis-Info von Switches, Druckern usw. | Community-String konfigurieren |

---

### 2. Daten bearbeiten

Jede Zelle in der Tabelle ist direkt editierbar.

| Zellfarbe | Bedeutung |
|---|---|
| 🟡 **Gelb / kursiv** | Automatischer Vorschlag — prüfen und ggf. anpassen |
| ⬜ **Weiß / normal** | Manuell eingetragener oder bestätigter Wert |
| ⬛ **Dunkelgrau** | Schreibgeschütztes Scan-Ergebnis |

**Doppelklick** auf eine Zeile öffnet den vollständigen Bearbeitungsdialog mit drei Tabs:

- **🔍 Scan-Ergebnis** — alle erkannten Hardware-Daten im Überblick
- **📋 Dokumentation** — alle i-doit-Felder inkl. Sysid und Dokumentationsgrad-Balken
- **🖱 Peripherie** *(nur bei Clients)* — angeschlossene Geräte verwalten

---

### 3. Zugangsdaten konfigurieren

Über **⚙ Konfigurieren** können mehrere Zugangsdaten pro Protokoll hinterlegt werden.  
AutoDoku probiert sie beim Deep Scan automatisch der Reihe nach durch.

| Protokoll | Format |
|---|---|
| WMI | `DOMAIN\user` oder `user` + Passwort |
| SSH (Passwort) | `user` + Passwort |
| SSH (Key) | `user\|/pfad/zum/key` (Benutzername mit Pipe + Pfad) |
| SNMP | Community-String (z. B. `public`) |

Zugangsdaten werden im **Windows Credential Manager** verschlüsselt gespeichert.

---

### 4. CSV exportieren

Über **⬇ Exportieren als CSV…** wird eine i-doit-kompatible CSV-Datei erzeugt:

- Jedes Gerät = eine Zeile
- Peripherie = direkt folgende Zeilen mit ererbtem Standort/Raum
- **Sysid-Spalte als erste Spalte** — bei gesetzter Sysid aktualisiert i-doit das bestehende Objekt

**Import in i-doit:** *Extras → Import → CSV-Import*

---

## i-doit Workflow

```
Erst-Scan (Sysid leer)
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│ AutoDoku scannt │────▶│ CSV exportieren  │────▶│ i-doit Import          │
│ Netzwerk        │     │ Sysid-Spalte leer│     │ → neue Objekte anlegen │
└─────────────────┘     └──────────────────┘     └──────────┬─────────────┘
                                                             │
                                                   i-doit vergibt Sysids
                                                             │
Folge-Scan (Sysid befüllt)                                   ▼
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│ Sysids aus      │────▶│ Nächster Scan    │────▶│ i-doit Import          │
│ i-doit eintragen│     │ → CSV exportieren│     │ → Objekte aktualisieren│
└─────────────────┘     └──────────────────┘     └────────────────────────┘
```

**Sysid aus i-doit ermitteln:**
- Objekt in i-doit öffnen → **Übersicht → Sysid**
- Oder per CSV-Export aus i-doit (Spalte `Sysid`)

---

## Konfiguration

Die Datei `config.json` liegt neben der `AutoDoku.exe` und kann mit einem Texteditor angepasst werden:

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `default_ip_range` | `192.168.1.0/24` | Vorbelegter IP-Bereich im Eingabefeld |
| `scan_timeout` | `2` | Timeout in Sekunden pro Host (ARP + Ports) |
| `max_threads` | `50` | Maximale parallele Scan-Threads |
| `default_ports` | `[22, 80, 135, 161, 443, 3389, 9100]` | Ports für Gerättyp-Erkennung |
| `snmp_community` | `public` | Standard SNMP Community-String |
| `log_level` | `INFO` | Protokoll-Detailgrad (`DEBUG`, `INFO`, `WARNING`) |
| `mock_mode` | `false` | Demo-Modus ohne echten Netzwerk-Scan |

Das Log (`autodoku.log`) und die Datenbank (`autodoku.db`) werden ebenfalls neben der EXE gespeichert.

---

## Architektur

```
AutoDoku/
├── main.py                    # Einstiegspunkt, Logging, Stylesheet, App-Icon
├── config.json                # Konfiguration
├── core/
│   ├── arp_sweep.py           # Windows SendARP – Host-Discovery ohne Npcap
│   ├── scanner.py             # Scan-Worker (QThread) mit WMI / SSH / SNMP
│   ├── device_classifier.py   # Gerättyp-Erkennung aus Vendor, Port, Hostname
│   ├── suggestions.py         # Proaktive Feld-Vorschläge
│   ├── vendor_lookup.py       # MAC-Vendor via manuf (Wireshark OUI, offline)
│   ├── port_scanner.py        # TCP-Connect Port-Scanner (kein nmap)
│   ├── wmi_connector.py       # WMI Deep Scan (Windows-Hosts)
│   ├── ssh_connector.py       # SSH Deep Scan (Linux-Hosts)
│   └── snmp_connector.py      # SNMP Basis-Scan (Switches, Drucker)
├── data/
│   ├── models.py              # Device, Peripheral, ScanSession Dataclasses
│   ├── session_store.py       # SQLite-Persistenz mit automatischer Migration
│   └── credential_store.py    # Windows Credential Manager via keyring
├── export/
│   └── idoit_csv_exporter.py  # i-doit CSV-Export (Sysid, Peripherie, alle Felder)
└── ui/
    ├── main_window.py         # Hauptfenster, Stats-Bar, Scan-Steuerung
    ├── result_table_widget.py # Inline-editierbare Geräte-Tabelle mit Vorschlägen
    ├── device_edit_dialog.py  # 3-Tab-Dialog: Scan / Dokumentation / Peripherie
    ├── peripheral_dialog.py   # Peripherie hinzufügen / bearbeiten
    ├── scan_config_dialog.py  # Credential-Verwaltung
    ├── progress_widget.py     # Fortschrittsanzeige
    ├── styles/dark_theme.qss  # Dark Theme (Windows-Blau #0078d4)
    └── assets/autodoku.svg    # App-Logo
```

**Stack:**

| Schicht | Technologie |
|---|---|
| GUI | PyQt6 |
| Datenbank | SQLite (automatisch migriert) |
| Netzwerk-Discovery | Windows `SendARP` API via ctypes — kein Npcap |
| Deep Scan | WMI (`wmi`), SSH (`paramiko`), SNMP (`pysnmp`) |
| MAC-Vendor-Lookup | `manuf` (Wireshark OUI-Datenbank, vollständig offline) |
| Credential-Speicher | Windows Credential Manager (`keyring`) |
| Build | PyInstaller 6.x (onefile, portable) |

---

## Systemvoraussetzungen

| Anforderung | Details |
|---|---|
| **Betriebssystem** | Windows 10 / 11 (64-bit) |
| **Netzwerk** | Selbes Layer-2-Segment wie die zu scannenden Hosts |
| **Rechte** | Normale Benutzerrechte für ARP-Scan ausreichend |
| **Npcap / nmap** | **Nicht erforderlich** |
| **Python** | 3.11+ nur beim Quellcode-Start oder EXE-Build benötigt |

> WMI Deep Scan erfordert, dass WMI-Remoting auf dem Zielhost erlaubt ist.  
> SSH Deep Scan erfordert einen laufenden SSH-Dienst auf dem Zielhost.

---

## Lizenz

MIT License — siehe [LICENSE](LICENSE).

---

<div align="center">

Gebaut für IT-Teams, die i-doit betreiben und die Erst-Katalogisierung beschleunigen wollen.

</div>
