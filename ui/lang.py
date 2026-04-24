"""Minimal UI translation module for AutoDoku.

Usage:
    from ui.lang import t, get_lang, set_lang, register

    label.setText(t("btn_scan"))          # Returns translated string
    register(my_retranslate_callback)     # Called on every language switch
"""
from __future__ import annotations

from typing import Callable

_LANG: str = "EN"
_CALLBACKS: list[Callable] = []

_STRINGS: dict[str, dict[str, str]] = {
    "EN": {
        # ── Top bar ───────────────────────────────────────────────────
        "btn_scan":    "▶  Start Scan",
        "btn_stop":    "■  Stop",
        "btn_config":  "⚙  Configure",
        "btn_import":  "⬆  Import CSV…",
        "btn_export":  "⬇  Export as CSV…",
        "lbl_ip_range": "IP Range:",
        "tip_wmi":     "WMI deep scan for Windows hosts (credentials required)",
        "tip_ssh":     "SSH deep scan for Linux hosts (credentials required)",
        "tip_snmp":    "SNMP scan for network devices (switches, printers)",
        "tip_import":  "Load a previous AutoDoku export to continue working",
        # ── Window / dialog titles ────────────────────────────────────
        "window_title":  "Network Scanner & i-doit Documentation",
        # ── Stats bar ─────────────────────────────────────────────────
        "stat_total":    "Total",
        "stat_clients":  "Clients",
        "stat_servers":  "Servers",
        "stat_switches": "Switches",
        "stat_printers": "Printers",
        "stat_other":    "Other",
        "hint_dblclick": "Double-click a row to edit details & peripherals",
        # ── Table column headers ──────────────────────────────────────
        "col_status":       "Status",
        "col_peripherals":  "Peripherals",
        "col_type":         "Type",
        "col_ip":           "IP Address",
        "col_mac":          "MAC Address",
        "col_manufacturer": "Manufacturer",
        "col_hostname":     "Hostname",
        "col_os":           "OS",
        "col_cpu":          "CPU",
        "col_ram":          "RAM (GB)",
        "col_model":        "Model",
        "col_serial":       "Serial No.",
        "col_location":     "Location",
        "col_room":         "Room",
        "col_department":   "Department",
        "col_contact":      "Contact",
        "col_cmdb_status":  "CMDB Status",
        "col_sysid":        "Sysid",
        "col_notes":        "Notes",
        # ── Progress / scan messages ──────────────────────────────────
        "scan_starting":   "Starting ARP sweep…",
        "scan_no_hosts":   "No hosts found.",
        "scan_progress":   "Scanned: {done}/{total}",
        "scan_aborted":    "Scan aborted.",
        "scan_done":       "Scan complete.",
        # ── Peripheral column cell text ───────────────────────────────
        "periph_suggestion": "🟡 {n} suggestion",
        "periph_count":      "🖱 {n}",
    },
    "DE": {
        # ── Top bar ───────────────────────────────────────────────────
        "btn_scan":    "▶  Scan starten",
        "btn_stop":    "■  Stopp",
        "btn_config":  "⚙  Einstellungen",
        "btn_import":  "⬆  CSV importieren…",
        "btn_export":  "⬇  Als CSV exportieren…",
        "lbl_ip_range": "IP-Bereich:",
        "tip_wmi":     "WMI-Tiefscan für Windows-Hosts (Zugangsdaten erforderlich)",
        "tip_ssh":     "SSH-Tiefscan für Linux-Hosts (Zugangsdaten erforderlich)",
        "tip_snmp":    "SNMP-Scan für Netzwerkgeräte (Switches, Drucker)",
        "tip_import":  "Vorherigen AutoDoku-Export laden, um weiterzuarbeiten",
        # ── Window / dialog titles ────────────────────────────────────
        "window_title":  "Netzwerkscanner & i-doit Dokumentation",
        # ── Stats bar ─────────────────────────────────────────────────
        "stat_total":    "Gesamt",
        "stat_clients":  "Clients",
        "stat_servers":  "Server",
        "stat_switches": "Switches",
        "stat_printers": "Drucker",
        "stat_other":    "Sonstiges",
        "hint_dblclick": "Doppelklick auf Zeile zum Bearbeiten",
        # ── Table column headers ──────────────────────────────────────
        "col_status":       "Status",
        "col_peripherals":  "Peripherie",
        "col_type":         "Typ",
        "col_ip":           "IP-Adresse",
        "col_mac":          "MAC-Adresse",
        "col_manufacturer": "Hersteller",
        "col_hostname":     "Hostname",
        "col_os":           "Betriebssystem",
        "col_cpu":          "CPU",
        "col_ram":          "RAM (GB)",
        "col_model":        "Modell",
        "col_serial":       "Seriennummer",
        "col_location":     "Standort",
        "col_room":         "Raum",
        "col_department":   "Abteilung",
        "col_contact":      "Ansprechpartner",
        "col_cmdb_status":  "CMDB-Status",
        "col_sysid":        "Sysid",
        "col_notes":        "Notizen",
        # ── Progress / scan messages ──────────────────────────────────
        "scan_starting":   "Starte ARP-Sweep…",
        "scan_no_hosts":   "Keine Hosts gefunden.",
        "scan_progress":   "Gescannt: {done}/{total}",
        "scan_aborted":    "Scan abgebrochen.",
        "scan_done":       "Scan abgeschlossen.",
        # ── Peripheral column cell text ───────────────────────────────
        "periph_suggestion": "🟡 {n} Vorschlag",
        "periph_count":      "🖱 {n}",
    },
}


def get_lang() -> str:
    """Return the current language code ('EN' or 'DE')."""
    return _LANG


def set_lang(lang: str) -> None:
    """Switch the active language and notify all registered callbacks."""
    global _LANG
    if lang not in _STRINGS:
        return
    _LANG = lang
    for cb in list(_CALLBACKS):
        try:
            cb()
        except Exception:
            pass


def toggle_lang() -> str:
    """Toggle between EN and DE.  Returns the new language code."""
    new_lang = "DE" if _LANG == "EN" else "EN"
    set_lang(new_lang)
    return new_lang


def t(key: str) -> str:
    """Return the translated string for *key* in the current language.

    Falls back to English, then to the key itself if not found.
    """
    lang_dict = _STRINGS.get(_LANG, _STRINGS["EN"])
    return lang_dict.get(key, _STRINGS["EN"].get(key, key))


def register(callback: Callable) -> None:
    """Register *callback* to be called whenever the language changes."""
    if callback not in _CALLBACKS:
        _CALLBACKS.append(callback)
