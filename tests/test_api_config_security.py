import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from app.core.config import Config
from app.web.app import create_app


class ConfigSecurityAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self._temp_dir.name) / "config.yaml"
        self.config_path.write_text(
            yaml.safe_dump(
                {
                    "serial": {"port": "/dev/ttyUSB0", "baudrate": 115200},
                    "ntrip": {
                        "host": "caster.example.com",
                        "port": 2101,
                        "mountpoint": "TEST",
                        "username": "user1",
                        "password": "super-secret",
                    },
                    "reconnect": {"max_retries": 5, "retry_delay": 5.0},
                    "base_station": {
                        "latitude": 31.2,
                        "longitude": 120.7,
                        "altitude": 10.0,
                        "enable_arp_average": 0,
                    },
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def _make_client(self) -> TestClient:
        def config_factory() -> Config:
            return Config(str(self.config_path))

        self._patcher = patch("app.web.routes.api.Config", new=config_factory)
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

        return TestClient(create_app())

    def test_get_config_redacts_ntrip_password(self) -> None:
        client = self._make_client()
        response = client.get("/api/config")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["ntrip"]["password"], "")

    def test_update_config_blank_password_does_not_overwrite_secret(self) -> None:
        client = self._make_client()
        response = client.post(
            "/api/config",
            json={
                "serial.baudrate": "9600",
                "ntrip.password": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        saved = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["ntrip"]["password"], "super-secret")
        self.assertEqual(saved["serial"]["baudrate"], 9600)


if __name__ == "__main__":
    unittest.main()
