import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from app.core.config import Config as RealConfig
from app.web.app import create_app


class ConfigApiSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._config_path = Path(self._tmpdir.name) / "config.yaml"
        self._write_config(
            {
                "serial": {"port": "/dev/ttyUSB0", "baudrate": 115200},
                "ntrip": {
                    "host": "caster.example.com",
                    "port": 2101,
                    "mountpoint": "RTCM32",
                    "username": "rtk-user",
                    "password": "very-secret-password",
                },
                "reconnect": {"max_retries": 5, "retry_delay": 1.0},
                "base_station": {
                    "latitude": 39.9,
                    "longitude": 116.4,
                    "altitude": 50.0,
                    "enable_arp_average": 0,
                },
            }
        )

        config_path = str(self._config_path)

        class TestConfig(RealConfig):
            def __init__(self, config_path_override: str = "config.yaml"):
                super().__init__(config_path=config_path)

        self._config_patch = patch("app.web.routes.api.Config", TestConfig)
        self._config_patch.start()
        self._client = TestClient(create_app())

    def tearDown(self) -> None:
        self._config_patch.stop()
        self._tmpdir.cleanup()

    def test_get_config_redacts_ntrip_password(self) -> None:
        response = self._client.get("/api/config")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["ntrip"]["password"], "")

    def test_update_config_keeps_existing_password_when_empty(self) -> None:
        response = self._client.post(
            "/api/config",
            json={"ntrip": {"password": ""}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        saved_password = self._read_saved_password()
        self.assertEqual(saved_password, "very-secret-password")

    def test_update_config_allows_password_rotation(self) -> None:
        response = self._client.post(
            "/api/config",
            json={"ntrip": {"password": "new-secret-password"}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        saved_password = self._read_saved_password()
        self.assertEqual(saved_password, "new-secret-password")

    def _read_saved_password(self) -> str:
        with open(self._config_path, "r", encoding="utf-8") as file:
            config_data = yaml.safe_load(file) or {}
        return config_data["ntrip"]["password"]

    def _write_config(self, data: dict) -> None:
        with open(self._config_path, "w", encoding="utf-8") as file:
            yaml.safe_dump(data, file, allow_unicode=True, default_flow_style=False)


if __name__ == "__main__":
    unittest.main()
