import unittest

from app.web_security import drop_empty_password, mask_sensitive_config


class ApiSecurityHelpersTest(unittest.TestCase):
    def test_mask_sensitive_config_hides_password(self):
        config_data = {
            "ntrip": {"host": "example.com", "password": "super-secret"},
            "serial": {"port": "/dev/ttyUSB0"},
        }

        masked = mask_sensitive_config(config_data)

        self.assertEqual("", masked["ntrip"]["password"])
        self.assertEqual("super-secret", config_data["ntrip"]["password"])

    def test_drop_empty_password_removes_password_field(self):
        update_data = {
            "ntrip": {"host": "caster.example.com", "password": "   "},
        }

        sanitized = drop_empty_password(update_data)

        self.assertNotIn("password", sanitized["ntrip"])
        self.assertEqual("caster.example.com", sanitized["ntrip"]["host"])

    def test_drop_empty_password_keeps_non_empty_password(self):
        update_data = {
            "ntrip": {"password": "new-secret"},
        }

        sanitized = drop_empty_password(update_data)

        self.assertEqual("new-secret", sanitized["ntrip"]["password"])


if __name__ == "__main__":
    unittest.main()
