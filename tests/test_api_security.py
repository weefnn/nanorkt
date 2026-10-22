import unittest

from app.web_security import (
    drop_empty_password,
    is_sensitive_api_allowed,
    mask_sensitive_config,
)


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

    def test_sensitive_api_allows_loopback_without_token(self):
        self.assertTrue(
            is_sensitive_api_allowed(
                client_host="127.0.0.1",
                provided_token=None,
                configured_token="expected-token",
            )
        )

    def test_sensitive_api_rejects_remote_without_configured_token(self):
        self.assertFalse(
            is_sensitive_api_allowed(
                client_host="192.168.1.50",
                provided_token="any-token",
                configured_token="",
            )
        )

    def test_sensitive_api_allows_remote_with_valid_token(self):
        self.assertTrue(
            is_sensitive_api_allowed(
                client_host="192.168.1.50",
                provided_token="right-token",
                configured_token="right-token",
            )
        )

    def test_sensitive_api_rejects_remote_with_invalid_token(self):
        self.assertFalse(
            is_sensitive_api_allowed(
                client_host="192.168.1.50",
                provided_token="wrong-token",
                configured_token="right-token",
            )
        )


if __name__ == "__main__":
    unittest.main()
