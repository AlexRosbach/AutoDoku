"""Credential storage backed by the OS keychain via the keyring library.

Supports multiple credential sets per service so that the scanner can
try them in sequence.  Credentials are serialised as JSON and stored as a
single keyring entry per service.

On Windows, the keyring backend is the Windows Credential Manager.
"""
from __future__ import annotations

import json
import logging

import keyring

logger = logging.getLogger(__name__)

SERVICE_WMI  = "autodoku_wmi"
SERVICE_SSH  = "autodoku_ssh"
SERVICE_SNMP = "autodoku_snmp"

_JSON_KEY = "__credentials_json__"

# ---------------------------------------------------------------------------
# Multi-credential API
# ---------------------------------------------------------------------------

def save_credentials_list(service: str, creds: list[tuple[str, str]]) -> None:
    """Persist a list of (username, password) pairs for *service*.

    Replaces any previously stored credentials for the service.
    """
    try:
        data = json.dumps([[u, p] for u, p in creds])
        keyring.set_password(service, _JSON_KEY, data)
        logger.info("Saved %d credential(s) for service '%s'", len(creds), service)
    except keyring.errors.KeyringError as exc:
        logger.error("Failed to save credentials for '%s': %s", service, exc)


def get_credentials_list(service: str) -> list[tuple[str, str]]:
    """Retrieve all stored (username, password) pairs for *service*.

    Returns an empty list if nothing is stored.
    """
    try:
        raw = keyring.get_password(service, _JSON_KEY)
        if raw:
            return [(u, p) for u, p in json.loads(raw)]
    except (keyring.errors.KeyringError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to load credentials for '%s': %s", service, exc)
    return []


def delete_credentials(service: str) -> None:
    """Remove all stored credentials for *service*."""
    try:
        keyring.delete_password(service, _JSON_KEY)
        logger.info("Credentials deleted for service '%s'", service)
    except keyring.errors.KeyringError as exc:
        logger.warning("Could not delete credentials for '%s': %s", service, exc)


# ---------------------------------------------------------------------------
# Single-credential convenience wrappers (backward-compatible)
# ---------------------------------------------------------------------------

def save_credentials(service: str, username: str, password: str) -> None:
    """Store a single credential for *service*, replacing any existing list."""
    save_credentials_list(service, [(username, password)])


def get_credentials(service: str) -> tuple[str, str] | None:
    """Return the first stored credential for *service*, or None."""
    lst = get_credentials_list(service)
    return lst[0] if lst else None
