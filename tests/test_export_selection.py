import csv
import tempfile
import unittest
from pathlib import Path

from data.models import Device, Peripheral, ScanSession
from export import idoit_csv_exporter


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


if __name__ == "__main__":
    unittest.main()
