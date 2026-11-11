import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from app.core.config import Config as CoreConfig
from app.web.app import create_app
from app.web.routes import api as api_routes


def _write_config(path: Path, password: str) -> None:
    config = {
        "serial": {"port": "/dev/ttyUSB0", "baudrate": 115200},
        "ntrip": {
            "host": "caster.example.com",
            "port": 2101,
            "mountpoint": "RTCM32",
            "username": "demo",
            "password": password,
        },
        "reconnect": {"max_retries": 5, "retry_delay": 5.0},
        "base_station": {
            "latitude": 0.0,
            "longitude": 0.0,
            "altitude": 0.0,
            "enable_arp_average": 0,
        },
    }
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")


class ConfigSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.yaml"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _temp_config_class(self):
        config_path = self.config_path

        class TempConfig(CoreConfig):
            def __init__(self):
                super().__init__(str(config_path))

        return TempConfig

    def test_get_config_masks_ntrip_password(self) -> None:
        _write_config(self.config_path, password="super-secret")
        temp_config = self._temp_config_class()

        with patch.object(api_routes, "Config", temp_config):
            with patch.object(api_routes, "ensure_api_access", return_value=None):
                with TestClient(create_app()) as client:
                    response = client.get("/api/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["ntrip"]["password"],
            api_routes.MASKED_PASSWORD,
        )

    def test_update_config_keeps_password_when_mask_is_submitted(self) -> None:
        _write_config(self.config_path, password="keep-this-password")
        temp_config = self._temp_config_class()

        payload = {
            "ntrip.host": "updated.example.com",
            "ntrip.password": api_routes.MASKED_PASSWORD,
        }

        with patch.object(api_routes, "Config", temp_config):
            with patch.object(api_routes, "ensure_api_access", return_value=None):
                with TestClient(create_app()) as client:
                    response = client.post("/api/config", json=payload)

        self.assertEqual(response.status_code, 200)
        saved = CoreConfig(str(self.config_path)).to_dict()
        self.assertEqual(saved["ntrip"]["host"], "updated.example.com")
        self.assertEqual(saved["ntrip"]["password"], "keep-this-password")


if __name__ == "__main__":
    unittest.main()
