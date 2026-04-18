"""SNMP v2c connector for network devices.

Queries sysDescr and sysName from the standard MIB-II system group.
Supports pysnmp >= 6.x (asyncio-first API) with a synchronous wrapper.
"""
from __future__ import annotations
import asyncio
import logging

logger = logging.getLogger(__name__)

# Standard MIB-II OIDs
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"

SNMP_AVAILABLE = False

try:
    # pysnmp 6.x asyncio API
    from pysnmp.hlapi.v3arch.asyncio import (
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        get_cmd,
    )
    SNMP_AVAILABLE = True
    _API_VERSION = "v6"
except ImportError:
    try:
        # pysnmp 4.x / 5.x synchronous hlapi
        from pysnmp.hlapi import (  # type: ignore[no-redef]
            CommunityData,
            ContextData,
            ObjectIdentity,
            ObjectType,
            SnmpEngine,
            UdpTransportTarget,
            getCmd,
        )
        SNMP_AVAILABLE = True
        _API_VERSION = "v4"
        get_cmd = None  # type: ignore[assignment]
    except ImportError:
        logger.warning("pysnmp is not available – SNMP scan will be skipped")
        _API_VERSION = "none"


def scan(ip: str, community: str = "public") -> dict[str, str]:
    """Query sysDescr and sysName via SNMP v2c.

    Args:
        ip:        Target IP address.
        community: SNMP community string (default: ``"public"``).

    Returns:
        Dict with keys ``sysDescr`` and ``sysName`` (may be empty strings).
        Returns an empty dict if SNMP is unavailable or the host does not respond.
    """
    if not SNMP_AVAILABLE:
        return {}

    if _API_VERSION == "v6":
        return _scan_v6(ip, community)
    return _scan_v4(ip, community)


def _scan_v6(ip: str, community: str) -> dict[str, str]:
    """SNMP query using pysnmp 6.x asyncio API."""

    async def _query() -> dict[str, str]:
        result: dict[str, str] = {}
        engine = SnmpEngine()
        for label, oid in [("sysDescr", OID_SYS_DESCR), ("sysName", OID_SYS_NAME)]:
            try:
                err_ind, err_status, _, var_binds = await get_cmd(
                    engine,
                    CommunityData(community),
                    await UdpTransportTarget.create((ip, 161), timeout=2, retries=1),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid)),
                )
            except Exception as exc:
                logger.warning("SNMP v6 error for %s oid %s: %s", ip, oid, exc)
                break

            if err_ind:
                logger.warning("SNMP error indication for %s: %s", ip, err_ind)
                break
            if err_status:
                logger.warning("SNMP error status for %s: %s", ip, err_status.prettyPrint())
                break

            for var_bind in var_binds:
                result[label] = str(var_bind[1])
        engine.close_dispatcher()
        return result

    try:
        return asyncio.run(_query())
    except Exception as exc:
        logger.warning("SNMP scan failed for %s: %s", ip, exc)
        return {}


def _scan_v4(ip: str, community: str) -> dict[str, str]:
    """SNMP query using pysnmp 4.x/5.x synchronous API."""
    result: dict[str, str] = {}
    for label, oid in [("sysDescr", OID_SYS_DESCR), ("sysName", OID_SYS_NAME)]:
        try:
            err_ind, err_status, _, var_binds = next(
                getCmd(  # type: ignore[name-defined]
                    SnmpEngine(),
                    CommunityData(community),
                    UdpTransportTarget((ip, 161), timeout=2, retries=1),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid)),
                )
            )
        except Exception as exc:
            logger.warning("SNMP v4 error for %s oid %s: %s", ip, oid, exc)
            break

        if err_ind:
            logger.warning("SNMP error indication for %s: %s", ip, err_ind)
            break
        if err_status:
            logger.warning("SNMP error status for %s: %s", ip, err_status.prettyPrint())
            break

        for var_bind in var_binds:
            result[label] = str(var_bind[1])

    return result
