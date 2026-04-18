# AutoDoku

Portabler Windows-Netzwerkscanner mit i-doit CSV-Export.

AutoDoku scannt ein lokales Netzwerk, liest Hardware- und OS-Details aus
Windows- (WMI), Linux- (SSH) und Netzwerkgeräten (SNMP) aus und exportiert
die Ergebnisse als i-doit-kompatible CSV-Datei – ohne Installation, ohne
Cloud-Abhängigkeit.

---

## Screenshots

> _Screenshots folgen nach dem ersten Windows-Build._

---

## Features (MVP)

| Feature | Detail |
|---|---|
| **Host-Discovery** | ARP-Sweep + ICMP über konfigurierbaren IP-Bereich (CIDR) |
| **Port-Scan** | TCP-Ports 22, 80, 135, 161, 443, 3389, 9100 via nmap |
| **WMI-Scan** | Hostname, OS, RAM, CPU, Seriennummer, Hersteller/Modell |
| **SSH-Scan** | `uname -a` + `dmidecode` für Linux/Unix-Hosts |
| **SNMP-Scan** | sysDescr + sysName (v2c) für Netzwerkgeräte |
| **Klassifizierung** | CLIENT · SERVER · PRINTER · SWITCH · UNKNOWN |
| **Review-UI** | Standort, Abteilung, Notizen editierbar; Monitore anhängbar |
| **CSV-Export** | i-doit-kompatibel (UTF-8, Semikolon, `C__OBJTYPE__*`) |
| **Persistenz** | SQLite – letzter Scan wird beim Start automatisch geladen |
| **Credentials** | Windows Credential Manager via `keyring` |
| **Portabel** | Einzelne EXE (PyInstaller), keine Installation nötig |

---

## Voraussetzungen

### Laufzeit (Zielrechner)

| Software | Zweck | Download |
|---|---|---|
| **Windows 10/11** (64-bit) | Zielplattform | – |
| **nmap ≥ 7.9** | Port-Scan-Backend | https://nmap.org/download.html |
| **Npcap** (wird mit nmap installiert) | ARP-Sweep | im nmap-Installer enthalten |

> nmap muss auf dem **Zielrechner** installiert und im `PATH` verfügbar sein.
> Es kann nicht in die EXE gebündelt werden.

### Entwicklung (Build-Rechner)

- Python 3.9+
- Alle Pakete aus `requirements.txt`

---

## Schnellstart (Entwicklung)

```bash
# Repository klonen
git clone https://github.com/AlexRosbach/AutoDoku.git
cd AutoDoku

# Abhängigkeiten installieren
pip install -r requirements.txt

# Mock-Modus aktivieren (kein Netzwerk, kein nmap nötig)
# config.json → "mock_mode": true

# App starten
python main.py
```

Im Mock-Modus erscheinen 5 vordefinierte Beispielgeräte (CLIENT, SERVER,
SWITCH, PRINTER) in der Tabelle – der komplette UI-Workflow ist ohne
Netzwerkzugang testbar.

---

## EXE bauen (Windows)

```bash
pip install -r requirements.txt
pyinstaller autodoku.spec
```

Die fertige `AutoDoku.exe` liegt in `dist/`. Sie enthält alle Python-
Abhängigkeiten und die QSS-Datei. Nmap und Npcap müssen separat installiert
sein.

---

## Bedienung

### 1. Scan starten

1. IP-Bereich eingeben (z. B. `192.168.1.0/24`)
2. Optionale Tiefen-Scans aktivieren: **WMI**, **SSH**, **SNMP**
3. Credentials unter **Konfigurieren** hinterlegen
4. **Scan starten** klicken – Geräte erscheinen live in der Tabelle

### 2. Gerät bearbeiten

Doppelklick auf eine Zeile öffnet den Editier-Dialog:

- Standort, Abteilung, Seriennummer, Notizen eintragen
- Bei **CLIENT**-Geräten: Monitore über **Monitor hinzufügen** anhängen
  (Hersteller, Modell, Seriennummer)

### 3. CSV exportieren

**Exportieren (CSV)** → Datei speichern → in i-doit importieren:
*Extras → Import → CSV-Import*

---

## Projektstruktur

```
AutoDoku/
├── main.py                        # Einstiegspunkt, Logging, QApplication
├── config.json                    # Laufzeitkonfiguration
├── autodoku.spec                  # PyInstaller Build-Konfiguration
├── requirements.txt
│
├── core/
│   ├── scanner.py                 # QThread-Scan-Orchestrator
│   ├── arp_sweep.py               # ARP-Host-Discovery (scapy)
│   ├── port_scanner.py            # TCP-Port-Scan (python-nmap)
│   ├── wmi_connector.py           # WMI Deep-Scan (Windows)
│   ├── ssh_connector.py           # SSH Deep-Scan (paramiko)
│   ├── snmp_connector.py          # SNMP v2c (pysnmp)
│   └── device_classifier.py      # Port-basierte Geräteklassifizierung
│
├── data/
│   ├── models.py                  # Dataclasses: Device, Monitor, ScanSession
│   ├── session_store.py           # SQLite CRUD
│   └── credential_store.py       # Keyring-Wrapper
│
├── export/
│   └── idoit_csv_exporter.py     # i-doit CSV-Export
│
├── ui/
│   ├── main_window.py             # Hauptfenster
│   ├── result_table_widget.py     # Geräte-Tabelle
│   ├── device_edit_dialog.py      # Editier-Dialog
│   ├── monitor_suggest_dialog.py  # Monitor-Subdialog
│   ├── scan_config_dialog.py      # Credentials-Dialog
│   ├── progress_widget.py         # Fortschrittsbalken-Widget
│   └── styles/dark_theme.qss      # Dark-Mode-Stylesheet
│
└── tests/
```

---

## Konfiguration (`config.json`)

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `default_ip_range` | `192.168.1.0/24` | Vorausgefüllter IP-Bereich |
| `scan_timeout` | `2` | ARP-Timeout in Sekunden |
| `max_threads` | `50` | Parallele Host-Scans |
| `default_ports` | `[22,80,135,161,443,3389,9100]` | Zu scannende Ports |
| `snmp_community` | `public` | Standard SNMP Community |
| `log_level` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `mock_mode` | `false` | `true` für Offline-Entwicklung |

---

## CSV-Format (i-doit)

Trennzeichen: `;` · Encoding: UTF-8 · Erste Zeile: Spaltenheader

```
Objekt-Typ;Bezeichnung;IP-Adresse;MAC-Adresse;Hostname;Betriebssystem;Hersteller;Modell;Seriennummer;RAM (GB);CPU;Standort;Abteilung;Notizen
C__OBJTYPE__CLIENT;PC-OFFICE-01;192.168.1.10;aa:bb:cc:dd:ee:02;PC-OFFICE-01;Windows 11 Pro;Dell;OptiPlex 7090;SN0001;16;Intel Core i7-10700;Büro 1;IT;
C__OBJTYPE__MONITOR;U2722D;;;;;;;Dell;U2722D;SN-MON-01;;;;;
C__OBJTYPE__SERVER;SRV-DC-01;192.168.1.20;aa:bb:cc:dd:ee:03;SRV-DC-01;Windows Server 2022;HP;ProLiant DL380;SN0002;64;Intel Xeon Gold 6226R;;;
```

i-doit-Objekttyp-Konstanten:

| Gerätetyp | Konstante |
|---|---|
| Client / PC | `C__OBJTYPE__CLIENT` |
| Server | `C__OBJTYPE__SERVER` |
| Drucker | `C__OBJTYPE__PRINTER` |
| Switch / Router | `C__OBJTYPE__SWITCH` |
| Unbekannt | `C__OBJTYPE__DEVICE` |
| Monitor | `C__OBJTYPE__MONITOR` |

---

## Tech Stack

| Paket | Zweck |
|---|---|
| [PyQt6](https://pypi.org/project/PyQt6/) | UI-Framework |
| [python-nmap](https://pypi.org/project/python-nmap/) | Port-Scan |
| [scapy](https://scapy.net/) | ARP-Sweep |
| [wmi](https://pypi.org/project/WMI/) + [pywin32](https://pypi.org/project/pywin32/) | WMI (Windows only) |
| [paramiko](https://www.paramiko.org/) | SSH |
| [pysnmp](https://pypi.org/project/pysnmp/) | SNMP |
| [keyring](https://pypi.org/project/keyring/) | Credential Manager |
| [PyInstaller](https://pyinstaller.org/) | EXE-Packaging |

---

## Roadmap

- **v1.1** – Automatischer Re-Scan / Scheduling
- **v1.2** – i-doit REST-API-Anbindung (direkter Import ohne CSV)
- **v1.3** – LLDP/CDP-Nachbarschaftserkennung für Switch-Topologien
- **v1.4** – Ping-basiertes Monitoring (Verfügbarkeitshistorie)

---

## Lizenz

MIT License – siehe [LICENSE](LICENSE).
