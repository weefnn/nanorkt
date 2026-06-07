import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from app.core.config import Config as RealConfig
from app.web.routes import api as api_routes


class DummyRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class ApiConfigSecurityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.yaml"
        self._write_config("secret-pass")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, password: str):
        data = {
            "serial": {"port": "/dev/ttyUSB0", "baudrate": 115200},
            "ntrip": {
                "host": "caster.example.com",
                "port": 2101,
                "mountpoint": "MOUNT",
                "username": "user",
                "password": password,
            },
            "reconnect": {"max_retries": 5, "retry_delay": 5.0},
            "base_station": {
                "latitude": 31.0,
                "longitude": 120.0,
                "altitude": 50.0,
                "enable_arp_average": 0,
            },
        }
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)

    def _read_password(self) -> str:
        with self.config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data["ntrip"]["password"]

    def _patched_config(self):
        return patch(
            "app.web.routes.api.Config",
            new=lambda: RealConfig(str(self.config_path)),
        )

    async def test_get_config_masks_password(self):
        with self._patched_config():
            data = await api_routes.get_config()

        self.assertEqual(
            data["ntrip"]["password"],
            api_routes.PASSWORD_PLACEHOLDER,
        )

    async def test_update_config_keeps_password_for_placeholder(self):
        request = DummyRequest({"ntrip.password": api_routes.PASSWORD_PLACEHOLDER})

        with self._patched_config():
            response = await api_routes.update_config(request)

        payload = json.loads(response.body.decode("utf-8"))
        self.assertTrue(payload["success"])
        self.assertEqual(self._read_password(), "secret-pass")

    async def test_update_config_allows_password_rotation(self):
        request = DummyRequest({"ntrip.password": "new-secret"})

        with self._patched_config():
            response = await api_routes.update_config(request)

        payload = json.loads(response.body.decode("utf-8"))
        self.assertTrue(payload["success"])
        self.assertEqual(self._read_password(), "new-secret")


if __name__ == "__main__":
    unittest.main()
