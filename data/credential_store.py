"""Credential storage backed by the OS keychain via the keyring library.

On Windows this uses the Windows Credential Manager.  The keyring API stores
(service, username) → password, but does not store the username itself.  We
work around this by storing the username under a fixed sentinel key so that
callers only need the service name to retrieve a full credential pair.
"""
from __future__ import annotations
import logging

import keyring

logger = logging.getLogger(__name__)

# Service-name constants shared with scanner.py and scan_config_dialog.py
SERVICE_WMI = "autodoku_wmi"
SERVICE_SSH = "autodoku_ssh"
SERVICE_SNMP = "autodoku_snmp"

_USERNAME_SENTINEL = "__username__"


def save_credentials(service: str, username: str, password: str) -> None:
    """Persist a username/password pair for *service* in the OS keychain.

    Args:
        service:  One of the SERVICE_* constants.
        username: The account name (e.g. DOMAIN\\user or community string).
        password: The secret to store.
    """
    try:
        keyring.set_password(service, _USERNAME_SENTINEL, username)
        keyring.set_password(service, username, password)
        logger.info("Credentials saved for service '%s'", service)
    except keyring.errors.KeyringError as exc:
        logger.error("Failed to save credentials for '%s': %s", service, exc)


def get_credentials(service: str) -> tuple[str, str] | None:
    """Retrieve the stored (username, password) pair for *service*.

    Returns:
        A (username, password) tuple, or None if no credentials are stored.
    """
    try:
        username = keyring.get_password(service, _USERNAME_SENTINEL)
        if username is None:
            return None
        password = keyring.get_password(service, username) or ""
        return (username, password)
    except keyring.errors.KeyringError as exc:
        logger.error("Failed to retrieve credentials for '%s': %s", service, exc)
        return None


def delete_credentials(service: str) -> None:
    """Remove stored credentials for *service* from the OS keychain."""
    try:
        username = keyring.get_password(service, _USERNAME_SENTINEL)
        if username:
            keyring.delete_password(service, username)
        keyring.delete_password(service, _USERNAME_SENTINEL)
        logger.info("Credentials deleted for service '%s'", service)
    except keyring.errors.KeyringError as exc:
        logger.warning("Could not delete credentials for '%s': %s", service, exc)
