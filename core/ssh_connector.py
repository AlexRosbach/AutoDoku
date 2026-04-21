"""SSH deep-scan connector for Linux/Unix hosts.

Connects via paramiko, runs several lightweight read-only commands, and parses
the output into a normalised hardware/OS detail dict.

Commands used (all non-destructive, no write access required):
  hostname          → device hostname
  lsb_release -d   → human-readable OS name (Ubuntu 22.04 LTS etc.)
  uname -sr        → kernel fallback if lsb_release is unavailable
  lscpu             → CPU model name
  free -m           → total RAM in MiB (converted to GB)
  sudo dmidecode -t system  → manufacturer, model, serial number
"""
from __future__ import annotations

import logging
import re

import paramiko

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 12   # seconds for TCP connect + SSH handshake
CMD_TIMEOUT     = 10   # seconds per individual command

_CMDS: dict[str, str] = {
    "hostname":   "hostname",
    "os":         "lsb_release -d 2>/dev/null | cut -d: -f2 | xargs || uname -sr",
    "cpu":        (
        "lscpu 2>/dev/null | grep -i 'model name' | head -1 | cut -d: -f2 | xargs"
        " || grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs"
    ),
    "ram":        "free -m 2>/dev/null | awk 'NR==2{print $2}'",
    "dmidecode":  (
        "sudo dmidecode -t system 2>/dev/null"
        " || dmidecode -t system 2>/dev/null"
    ),
}


def scan(
    ip: str,
    username: str,
    password: str | None = None,
    key_path: str | None = None,
) -> dict[str, object]:
    """Collect OS and hardware details from a Linux/Unix host via SSH.

    Args:
        ip:       Target IP address.
        username: SSH login name.
        password: Password for password-based auth.
        key_path: Path to a private key file for key-based auth.

    Returns:
        Dict with keys: hostname, os, cpu, ram_gb, manufacturer, model, serial.
        Returns an empty dict on any connection or auth failure so the caller
        can safely proceed to the next credential set.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict[str, object] = {
        "hostname": ip,
        "username": username,
        "timeout":  CONNECT_TIMEOUT,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if key_path:
        connect_kwargs["key_filename"] = key_path
        connect_kwargs["look_for_keys"] = True
    elif password:
        connect_kwargs["password"] = password

    try:
        client.connect(**connect_kwargs)  # type: ignore[arg-type]
        logger.info("SSH connected to %s as %s", ip, username)
        raw: dict[str, str] = {}
        for label, cmd in _CMDS.items():
            try:
                _, stdout, _ = client.exec_command(cmd, timeout=CMD_TIMEOUT)
                raw[label] = stdout.read().decode(errors="replace").strip()
            except Exception as exc:
                logger.debug("SSH cmd '%s' failed on %s: %s", label, ip, exc)
                raw[label] = ""
        return _parse(raw, ip)

    except paramiko.AuthenticationException:
        logger.warning("SSH authentication failed for %s (user: %s) – trying next credential", ip, username)
        return {}
    except paramiko.SSHException as exc:
        logger.warning("SSH error for %s: %s", ip, exc)
        return {}
    except OSError as exc:
        logger.warning("SSH connection error for %s: %s", ip, exc)
        return {}
    finally:
        client.close()


def _parse(raw: dict[str, str], ip: str = "") -> dict[str, object]:
    """Extract structured fields from raw SSH command output."""
    result: dict[str, object] = {}

    # Hostname
    hostname = raw.get("hostname", "").strip()
    if hostname and hostname.lower() not in ("localhost", "localhost.localdomain"):
        result["hostname"] = hostname

    # OS – prefer lsb_release, fall back to uname
    os_str = raw.get("os", "").strip()
    if os_str:
        result["os"] = os_str

    # CPU
    cpu = raw.get("cpu", "").strip()
    if cpu:
        result["cpu"] = cpu

    # RAM – free -m gives MiB, convert to GB (rounded)
    ram_raw = raw.get("ram", "").strip()
    if ram_raw:
        try:
            ram_mib = int(ram_raw.split()[0])
            result["ram_gb"] = max(1, round(ram_mib / 1024))
        except (ValueError, IndexError):
            pass

    # Hardware identity from dmidecode
    for line in raw.get("dmidecode", "").splitlines():
        stripped = line.strip()
        if stripped.startswith("Manufacturer:"):
            val = stripped.split(":", 1)[1].strip()
            if val and val.lower() not in ("", "to be filled by o.e.m.", "not specified"):
                result["manufacturer"] = val
        elif stripped.startswith("Product Name:"):
            val = stripped.split(":", 1)[1].strip()
            if val and val.lower() not in ("", "to be filled by o.e.m.", "not specified"):
                result["model"] = val
        elif stripped.startswith("Serial Number:"):
            val = stripped.split(":", 1)[1].strip()
            if val and val.lower() not in ("", "to be filled by o.e.m.", "not specified", "none"):
                result["serial"] = val

    logger.info("SSH scan parsed for %s: %s", ip, {k: v for k, v in result.items() if k != "raw"})
    return result
