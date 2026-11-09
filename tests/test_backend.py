import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from collectors.disks import parse_smartctl
from control import validate_control_request


class SmartctlParserTest(unittest.TestCase):
    def test_active_disk(self):
        payload = {
            "model_name": "Example Disk", "serial_number": "X", "user_capacity": {"bytes": 8000},
            "smart_status": {"passed": True}, "temperature": {"current": 31}, "power_on_time": {"hours": 900},
            "ata_smart_attributes": {"table": [{"id": 5, "raw": {"value": 0}}]},
        }
        parsed = parse_smartctl("/dev/sata2", json.dumps(payload), "", 0)
        self.assertEqual(parsed["state"], "active")
        self.assertEqual(parsed["temperature_c"], 31)
        self.assertEqual(parsed["reallocated_sectors"], 0)


class ControlRequestTest(unittest.TestCase):
    def test_screen_off_request(self):
        self.assertEqual(validate_control_request({"action": "screen_off"}), ("screen_off", None))

    def test_screen_off_until_reboot_requires_explicit_confirmation(self):
        action, error = validate_control_request({"action": "screen_off_boot"})
        self.assertIsNone(action)
        self.assertEqual(error, "screen off until reboot confirmation required")
        self.assertEqual(
            validate_control_request({"action": "screen_off_boot", "confirm": "screen_off_boot"}),
            ("screen_off_boot", None),
        )

    def test_shutdown_requires_explicit_confirmation(self):
        action, error = validate_control_request({"action": "shutdown"})
        self.assertIsNone(action)
        self.assertEqual(error, "shutdown confirmation required")
        self.assertEqual(
            validate_control_request({"action": "shutdown", "confirm": "shutdown"}),
            ("shutdown", None),
        )

    def test_standby_disk(self):
        parsed = parse_smartctl("/dev/sata3", "", "Device is in STANDBY mode", 2)
        self.assertEqual(parsed["state"], "standby")
        self.assertIsNone(parsed["temperature_c"])

    def test_bad_output_is_error(self):
        parsed = parse_smartctl("/dev/sata4", "not-json", "failed", 1)
        self.assertEqual(parsed["state"], "error")

    def test_synology_smartctl_65_text(self):
        text = """Device Model:     HUS728T8TALE600
User Capacity:    8,001,563,222,016 bytes [8.00 TB]
SMART overall-health self-assessment test result: PASSED
  5 Reallocated_Sector_Ct 0x0033 100 100 005 Pre-fail Always - 0
  9 Power_On_Hours 0x0012 098 098 000 Old_age Always - 19781
194 Temperature_Celsius 0x0002 206 103 000 Old_age Always - 29 (Min/Max 16/58)
"""
        parsed = parse_smartctl("/dev/sata3", text, "", 0)
        self.assertEqual(parsed["temperature_c"], 29)
        self.assertEqual(parsed["power_on_hours"], 19781)
        self.assertEqual(parsed["reallocated_sectors"], 0)


if __name__ == "__main__":
    unittest.main()
