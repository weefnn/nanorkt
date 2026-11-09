import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from app.core.config import Config as ConfigImpl
from app.web.app import create_app


def _config_factory(config_path: Path):
    def _factory():
        return ConfigImpl(str(config_path))
    return _factory


class ApiSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.yaml"
        self.config_path.write_text(
            yaml.safe_dump(
                {
                    "serial": {"port": "/dev/ttyUSB0", "baudrate": 115200},
                    "ntrip": {
                        "host": "caster.example.com",
                        "port": 2101,
                        "mountpoint": "TEST",
                        "username": "user",
                        "password": "super-secret",
                    },
                    "reconnect": {"max_retries": 5, "retry_delay": 5.0},
                    "base_station": {
                        "latitude": 31.0,
                        "longitude": 120.0,
                        "altitude": 10.0,
                        "enable_arp_average": 0,
                    },
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

        self.client = TestClient(create_app())

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    def test_config_endpoint_rejects_remote_without_admin_token(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NANORKT_ADMIN_TOKEN", None)
            with patch("app.web.routes.api.Config", side_effect=_config_factory(self.config_path)):
                response = self.client.get("/api/config")

        self.assertEqual(response.status_code, 403)

    def test_config_endpoint_masks_password_when_authorized(self):
        with patch.dict(os.environ, {"NANORKT_ADMIN_TOKEN": "token-123"}, clear=False):
            with patch("app.web.routes.api.Config", side_effect=_config_factory(self.config_path)):
                response = self.client.get(
                    "/api/config",
                    headers={"X-Admin-Token": "token-123"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["ntrip"]["password"], "")
        self.assertEqual(payload["ntrip"]["username"], "user")

    def test_update_config_does_not_overwrite_password_with_empty_value(self):
        with patch.dict(os.environ, {"NANORKT_ADMIN_TOKEN": "token-123"}, clear=False):
            with patch("app.web.routes.api.Config", side_effect=_config_factory(self.config_path)):
                response = self.client.post(
                    "/api/config",
                    headers={"X-Admin-Token": "token-123"},
                    json={"ntrip.password": ""},
                )

        self.assertEqual(response.status_code, 200)
        saved = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["ntrip"]["password"], "super-secret")


if __name__ == "__main__":
    unittest.main()
