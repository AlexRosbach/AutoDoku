import csv
import tempfile
import unittest
from pathlib import Path

from data.models import Device, Peripheral, ScanSession
from export import idoit_csv_exporter
from export.csv_importer import import_csv


class ExportSelectionTest(unittest.TestCase):
    def test_export_skips_unselected_devices_and_their_peripherals(self):
        included = Device(hostname="included", ip="192.0.2.10")
        included.peripherals.append(
            Peripheral(device_id=included.id, peripheral_type="Monitor", model="U2722D")
        )
        excluded = Device(
            hostname="excluded",
            ip="192.0.2.20",
            include_in_export=False,
        )
        excluded.peripherals.append(
            Peripheral(device_id=excluded.id, peripheral_type="Monitor", model="P2422H")
        )
        session = ScanSession(devices=[included, excluded])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "export.csv"
            rows_written = idoit_csv_exporter.export(session, str(path))
            with path.open(newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle, delimiter=";"))

        self.assertEqual(rows_written, 2)
        self.assertEqual([row["Bezeichnung"] for row in rows], ["included", "U2722D"])
        self.assertNotIn("excluded", [row["Bezeichnung"] for row in rows])

    def test_export_includes_lanlens_validated_documentation_fields(self):
        device = Device(
            hostname="switch-linked-client",
            ip="192.0.2.55",
            mac="00:11:22:33:44:55",
            snmp_switch="core-switch",
            snmp_port="Gi1/0/12",
            tls_certificates="HTTPS 443 expires 2026-12-31",
            mdns_summary="_workstation._tcp.local",
            upnp_summary="urn:schemas-upnp-org:device:Basic:1",
            passive_discovery="LLDP neighbor: core-switch",
            identity_confidence="high",
        )
        session = ScanSession(devices=[device])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "export.csv"
            rows_written = idoit_csv_exporter.export(session, str(path))
            with path.open(newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle, delimiter=";"))

        self.assertEqual(rows_written, 1)
        self.assertEqual(rows[0]["SNMP-Switch"], "core-switch")
        self.assertEqual(rows[0]["SNMP-Port"], "Gi1/0/12")
        self.assertEqual(rows[0]["TLS-Zertifikate"], "HTTPS 443 expires 2026-12-31")
        self.assertEqual(rows[0]["mDNS"], "_workstation._tcp.local")
        self.assertEqual(rows[0]["UPnP/SSDP"], "urn:schemas-upnp-org:device:Basic:1")
        self.assertEqual(rows[0]["Passive Discovery"], "LLDP neighbor: core-switch")
        self.assertEqual(rows[0]["Identity Confidence"], "high")

    def test_import_preserves_lanlens_validated_documentation_fields(self):
        device = Device(
            hostname="client-01",
            ip="192.0.2.70",
            snmp_switch="access-switch",
            snmp_port="Port 7",
            tls_certificates="No TLS services",
            mdns_summary="client-01.local",
            upnp_summary="",
            passive_discovery="mDNS hostname observed",
            identity_confidence="medium",
        )
        session = ScanSession(devices=[device])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "export.csv"
            idoit_csv_exporter.export(session, str(path))
            imported = import_csv(str(path))

        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0].snmp_switch, "access-switch")
        self.assertEqual(imported[0].snmp_port, "Port 7")
        self.assertEqual(imported[0].tls_certificates, "No TLS services")
        self.assertEqual(imported[0].mdns_summary, "client-01.local")
        self.assertEqual(imported[0].passive_discovery, "mDNS hostname observed")
        self.assertEqual(imported[0].identity_confidence, "medium")


if __name__ == "__main__":
    unittest.main()
