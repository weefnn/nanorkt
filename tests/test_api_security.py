import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml
from fastapi.testclient import TestClient

from app.web.app import create_app


SAMPLE_CONFIG = {
    "serial": {"port": "/dev/ttyUSB0", "baudrate": 115200},
    "ntrip": {
        "host": "caster.example.com",
        "port": 2101,
        "mountpoint": "TEST",
        "username": "test-user",
        "password": "real-secret-password",
    },
    "reconnect": {"max_retries": 5, "retry_delay": 5.0},
    "base_station": {
        "latitude": 31.359069353,
        "longitude": 120.714640617,
        "altitude": 51.123,
        "enable_arp_average": 0,
    },
}


class TestAPISecurity(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old_cwd = os.getcwd()
        os.chdir(self._tmp.name)

        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(SAMPLE_CONFIG, f, allow_unicode=True)

        self._old_token = os.environ.get("NANORKT_ADMIN_TOKEN")
        os.environ.pop("NANORKT_ADMIN_TOKEN", None)

        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        self.client.close()

        if self._old_token is None:
            os.environ.pop("NANORKT_ADMIN_TOKEN", None)
        else:
            os.environ["NANORKT_ADMIN_TOKEN"] = self._old_token

        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def test_remote_config_read_requires_token(self) -> None:
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 403)

    def test_config_read_with_valid_token_masks_password(self) -> None:
        os.environ["NANORKT_ADMIN_TOKEN"] = "token-123"

        denied = self.client.get("/api/config")
        self.assertEqual(denied.status_code, 403)

        allowed = self.client.get(
            "/api/config",
            headers={"X-Admin-Token": "token-123"}
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.json()["ntrip"]["password"], "********")

    def test_masked_password_does_not_overwrite_real_password(self) -> None:
        os.environ["NANORKT_ADMIN_TOKEN"] = "token-123"

        payload = {
            "ntrip.host": "new-caster.example.com",
            "ntrip.password": "********"
        }

        response = self.client.post(
            "/api/config",
            headers={"X-Admin-Token": "token-123"},
            json=payload
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        saved = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
        self.assertEqual(saved["ntrip"]["host"], "new-caster.example.com")
        self.assertEqual(saved["ntrip"]["password"], "real-secret-password")

    def test_control_endpoint_requires_token(self) -> None:
        os.environ["NANORKT_ADMIN_TOKEN"] = "token-123"

        denied = self.client.post("/api/control", json={"action": "start"})
        self.assertEqual(denied.status_code, 403)

        fake_manager = Mock()
        fake_manager.is_running.return_value = False

        with patch("app.web.routes.api.get_manager", return_value=fake_manager):
            allowed = self.client.post(
                "/api/control",
                headers={"X-Admin-Token": "token-123"},
                json={"action": "start"}
            )

        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.json()["success"])
        fake_manager.start_service.assert_called_once()


if __name__ == "__main__":
    unittest.main()
