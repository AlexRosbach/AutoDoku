"""SSH deep-scan connector for Linux/Unix hosts.

Connects via paramiko, runs uname and dmidecode, and parses the output into
a normalised hardware/OS detail dict.
"""
from __future__ import annotations
import logging

import paramiko

logger = logging.getLogger(__name__)

_CMD_UNAME = "uname -a"
# dmidecode needs root; try with sudo first, fall back silently
_CMD_DMIDECODE = "sudo dmidecode -t system 2>/dev/null || dmidecode -t system 2>/dev/null"

CONNECT_TIMEOUT = 10


def scan(
    ip: str,
    username: str,
    password: str | None = None,
    key_path: str | None = None,
) -> dict[str, object]:
    """Collect OS and hardware details from a Linux host via SSH.

    Args:
        ip:       Target IP address.
        username: SSH login name.
        password: Password for password-based auth (mutually exclusive with key_path).
        key_path: Path to a private key file for key-based auth.

    Returns:
        Dict with keys: os, manufacturer, model, serial, hostname.
        Returns an empty dict on any connection or auth failure.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict[str, object] = {
        "hostname": ip,
        "username": username,
        "timeout": CONNECT_TIMEOUT,
    }
    if key_path:
        connect_kwargs["key_filename"] = key_path
    elif password:
        connect_kwargs["password"] = password

    try:
        client.connect(**connect_kwargs)  # type: ignore[arg-type]
        raw: dict[str, str] = {}

        for label, cmd in [("uname", _CMD_UNAME), ("dmidecode", _CMD_DMIDECODE)]:
            _, stdout, _ = client.exec_command(cmd)
            raw[label] = stdout.read().decode(errors="replace").strip()

        return _parse(raw)

    except paramiko.AuthenticationException:
        logger.warning("SSH authentication failed for %s", ip)
        return {}
    except paramiko.SSHException as exc:
        logger.warning("SSH error for %s: %s", ip, exc)
        return {}
    except OSError as exc:
        logger.warning("SSH connection error for %s: %s", ip, exc)
        return {}
    finally:
        client.close()


def _parse(raw: dict[str, str]) -> dict[str, object]:
    """Extract structured fields from raw SSH command output."""
    result: dict[str, object] = {"os": raw.get("uname", "")}

    for line in raw.get("dmidecode", "").splitlines():
        stripped = line.strip()
        if stripped.startswith("Manufacturer:"):
            result["manufacturer"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Product Name:"):
            result["model"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Serial Number:"):
            result["serial"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Version:") and "version" not in result:
            result["version"] = stripped.split(":", 1)[1].strip()

    return result
