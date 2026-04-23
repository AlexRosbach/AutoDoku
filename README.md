<div align="center">

<img src="ui/assets/autodoku.svg" alt="AutoDoku Logo" width="100" height="100" />

# AutoDoku

**Netzwerkscanner & i-doit Dokumentationsassistent für Windows**

[![Version](https://img.shields.io/badge/version-1.2.0-0078d4)](https://github.com/AlexRosbach/AutoDoku)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-0078d4)](https://github.com/AlexRosbach/AutoDoku)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab)](https://python.org)

AutoDoku scannt dein Netzwerk, erkennt Geräte automatisch und hilft dir, alle relevanten Felder für den i-doit-Import auszufüllen — mit proaktiven Vorschlägen, Inline-Bearbeitung, Peripherie-Verwaltung und vollständig CSV-basierter Persistenz (kein lokaler Datenbankserver).

</div>

---

## Features

- **Netzwerk-Discovery** via Windows `SendARP` API — kein Npcap, kein nmap, keine erhöhten Rechte nötig
- **MAC-Vendor-Lookup** offline via Wireshark OUI-Datenbank (`manuf`)
- **Automatische Geräteklassifikation** nach Hersteller, Hostname-Muster und offenen Ports; Windows 10/11 → `Client`, Windows Server → `Server`
- **Deep Scan** via WMI (Windows), SSH (Linux) und SNMP — liest CPU, RAM, OS, Modell, Seriennummer
- **Multi-Credential-Support** — mehrere Zugangsdaten pro Protokoll, werden der Reihe nach probiert; WMI-Versuche haben einen 20-Sekunden-Timeout
- **Automatischer Monitor-Vorschlag** — wird ein Client erkannt, legt AutoDoku automatisch einen Bildschirm-Peripherieeintrag an; der Nutzer trägt nur noch Modell und Seriennummer ein
- **Inline-editierbare Scan-Tabelle** — das Arbeitsdokument direkt im Scanner, kein separater Bearbeitungsschritt
- **Proaktive Feld-Vorschläge** (gelb markiert) für CMDB-Status, Standort, Raum, Abteilung, OS, Hostname uvm.
- **Vollständige i-doit-Felder** — Inventarnummer, CMDB-Status, Standort, Raum, Abteilung, Ansprechpartner, Sysid
- **Sysid-Feld** — beim CSV-Reimport werden bestehende i-doit-Objekte aktualisiert statt dupliziert
- **Peripherie-Verwaltung** pro Client — Monitor, Tastatur, Maus, Headset, Docking Station, VoIP, Drucker, Webcam uvm.
- **CSV-Export** im i-doit-kompatiblen Format — Geräte und Peripherie als separate Zeilen in einer Datei
- **CSV-Import** — früheren Export laden und nahtlos weiterarbeiten (keine lokale Datenbank nötig)
- **Vollständig in-memory** — keine SQLite-Datenbank, keine lokale Zwischenspeicherung; Daten leben nur im laufenden Prozess
- **Dokumentationsgrad-Anzeige** pro Gerät mit Fortschrittsbalken und Vorschlag-Zähler
- **Stats-Bar** — Live-Übersicht der Geräteanzahl nach Typ
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
| **WMI** | Hardware-Details von Windows-Hosts | Zugangsdaten hinterlegen, WMI-Remoting freischalten |
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
- **🖱 Peripherie** *(nur bei Clients)* — angeschlossene Geräte verwalten; vorgeschlagene Einträge (gelb) können direkt bearbeitet werden

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

- Jedes Gerät = eine Zeile mit menschenlesbarem `Objekt-Typ` (z. B. `Client`, `Server`)
- Peripherie = direkt folgende Zeilen mit ererbtem Standort/Raum
- **Sysid-Spalte als erste Spalte** — bei gesetzter Sysid aktualisiert i-doit das bestehende Objekt
- Vorgeschlagene Peripherie ohne Modell/Seriennummer wird beim Export automatisch übersprungen

**Import in i-doit:** *Extras → Import → CSV-Import*

---

### 5. CSV importieren (Arbeit fortsetzen)

Über **⬆ CSV importieren…** kann ein früherer AutoDoku-Export geladen werden:

- Alle Geräte und Peripherieobjekte werden rekonstruiert
- Sysids bleiben erhalten → nächster Export aktualisiert bestehende i-doit-Objekte
- AutoDoku speichert **nichts lokal** — der Export ist die einzige Persistenz

---

## WMI Deep Scan einrichten

Damit AutoDoku WMI-Daten von Windows-Hosts lesen kann, müssen auf dem **Ziel-PC** folgende Einstellungen vorgenommen werden.

### Schritt 1 — WMI-Dienst aktivieren

```powershell
# Als Administrator ausführen
Set-Service -Name winmgmt -StartupType Automatic
Start-Service winmgmt
```

### Schritt 2 — Firewall-Regeln freischalten

```powershell
# DCOM-Port 135
netsh advfirewall firewall add rule `
  name="AutoDoku WMI DCOM" `
  dir=in action=allow protocol=TCP localport=135

# WMI-Dienst (dynamische Ports)
netsh advfirewall firewall set rule group="Windows-Verwaltungsinstrumentation (WMI)" new enable=yes

# Alternativ — vordefinierte Regelgruppe aktivieren:
Enable-NetFirewallRule -DisplayGroup "Windows Management Instrumentation (WMI)"
```

### Schritt 3 — DCOM-Berechtigungen setzen

```powershell
# Benutzer der Gruppe "Distributed COM Users" hinzufügen
Add-LocalGroupMember -Group "Distributed COM Users" -Member "DOMAIN\ScanUser"

# Alternativ: Administratorgruppe verwenden (einfacher, aber weiter Zugriff)
Add-LocalGroupMember -Group "Administrators" -Member "DOMAIN\ScanUser"
```

### Schritt 4 — WMI-Namespace-Berechtigungen (falls nötig)

Wenn der Scan-Benutzer **kein** lokaler Administrator ist:

1. `wmimgmt.msc` öffnen
2. Rechtsklick auf **WMI-Steuerung (lokal)** → **Eigenschaften**
3. Tab **Sicherheit** → `Root\CIMV2` auswählen → **Sicherheit**
4. Benutzer hinzufügen und Rechte **Konto aktivieren**, **Remote-Aktivierung** setzen

### Schritt 5 — UAC-Fernzugriff (für lokale Konten)

Falls ein lokales (nicht Domänen-) Konto verwendet wird:

```powershell
# Registry-Eintrag setzt UAC für Remote-Zugriff außer Kraft
New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" `
  -Name LocalAccountTokenFilterPolicy -Value 1 -PropertyType DWORD -Force
```

> **Hinweis:** Diese Einstellung betrifft alle lokalen Konten. In Domänenumgebungen stattdessen ein Domänenkonto mit entsprechenden Rechten verwenden.

### Schritt 6 — Zugangsdaten in AutoDoku hinterlegen

In AutoDoku → **⚙ Konfigurieren** → WMI-Zugangsdaten hinzufügen:

- **Benutzername:** `DOMAIN\ScanUser` oder `.\lokaler_admin`
- **Passwort:** Passwort des Kontos

AutoDoku probiert alle hinterlegten Credential-Sets der Reihe nach durch und bricht beim ersten Erfolg ab. Jeder Versuch hat einen **20-Sekunden-Timeout**, damit ein hängendes DCOM-Handshake den Scan nicht blockiert.

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
│ Export aus      │────▶│ Sysids eintragen │────▶│ Nächster Scan → Export │
│ i-doit laden   │     │ + neuer Scan     │     │ → Objekte aktualisieren│
│ (CSV importieren│     │                  │     │                        │
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

Das Log (`autodoku.log`) wird neben der EXE gespeichert. Es gibt **keine Datenbank** — alle Daten leben nur im laufenden Prozess und werden via CSV persistiert.

---

## Architektur

```
AutoDoku/
├── main.py                    # Einstiegspunkt, Logging, Stylesheet, App-Icon
├── version.py                 # Versionsinformationen (__version__, __app_name__)
├── config.json                # Konfiguration
├── core/
│   ├── arp_sweep.py           # Windows SendARP – Host-Discovery ohne Npcap
│   ├── scanner.py             # Scan-Worker (QThread) mit WMI / SSH / SNMP
│   ├── device_classifier.py   # Gerättyp-Erkennung inkl. OS-basierter Reklassifikation
│   ├── suggestions.py         # Proaktive Feld-Vorschläge
│   ├── vendor_lookup.py       # MAC-Vendor via manuf (offline)
│   ├── port_scanner.py        # TCP-Connect Port-Scanner (kein nmap)
│   ├── wmi_connector.py       # WMI Deep Scan (Windows, mit 20s Timeout)
│   ├── ssh_connector.py       # SSH Deep Scan (Linux: hostname, CPU, RAM, OS)
│   └── snmp_connector.py      # SNMP Basis-Scan
├── data/
│   ├── models.py              # Device, Peripheral, ScanSession Dataclasses
│   └── credential_store.py    # Windows Credential Manager via keyring
├── export/
│   ├── idoit_csv_exporter.py  # i-doit CSV-Export (Sysid, Peripherie, alle Felder)
│   └── csv_importer.py        # AutoDoku-CSV reimportieren → list[Device]
└── ui/
    ├── main_window.py         # Hauptfenster, Stats-Bar, Import/Export
    ├── result_table_widget.py # Inline-editierbare Geräte-Tabelle mit Vorschlägen
    ├── device_edit_dialog.py  # 3-Tab-Dialog: Scan / Dokumentation / Peripherie
    ├── peripheral_dialog.py   # Peripherie hinzufügen / bearbeiten
    ├── scan_config_dialog.py  # Credential-Verwaltung
    ├── progress_widget.py     # Fortschrittsanzeige
    ├── styles/dark_theme.qss  # Dark Theme
    └── assets/autodoku.svg    # App-Logo
```

**Stack:**

| Schicht | Technologie |
|---|---|
| GUI | PyQt6 |
| Persistenz | CSV-Datei (kein Server, keine Datenbank) |
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

> WMI Deep Scan erfordert, dass WMI-Remoting auf dem Zielhost eingerichtet ist (→ Anleitung oben).  
> SSH Deep Scan erfordert einen laufenden SSH-Dienst auf dem Zielhost.

---

## Lizenz

MIT License — siehe [LICENSE](LICENSE).

---

<div align="center">

Gebaut für IT-Teams, die i-doit betreiben und die Erst-Katalogisierung beschleunigen wollen.

</div>
