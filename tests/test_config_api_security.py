import asyncio
import json
import os
import tempfile
import unittest

import yaml

from app.web.routes.api import get_config, update_config


class DummyRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


class ConfigApiSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_cwd = os.getcwd()
        os.chdir(self._tmpdir.name)

        self._write_config(
            {
                "serial": {"port": "/dev/ttyUSB0", "baudrate": 115200},
                "ntrip": {
                    "host": "caster.example.com",
                    "port": 2101,
                    "mountpoint": "RTCM32",
                    "username": "demo-user",
                    "password": "super-secret",
                },
                "reconnect": {"max_retries": 5, "retry_delay": 5.0},
                "base_station": {
                    "latitude": 39.9,
                    "longitude": 116.4,
                    "altitude": 50.0,
                    "enable_arp_average": 0,
                },
            }
        )

    def tearDown(self) -> None:
        os.chdir(self._old_cwd)
        self._tmpdir.cleanup()

    def _write_config(self, data) -> None:
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)

    def _read_config(self):
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_get_config_redacts_ntrip_password(self) -> None:
        payload = asyncio.run(get_config())
        self.assertEqual(payload["ntrip"]["password"], "")

    def test_update_config_keeps_existing_password_when_blank(self) -> None:
        response = asyncio.run(
            update_config(
                DummyRequest(
                    {
                "ntrip.host": "new-caster.example.com",
                "ntrip.password": "",
                    }
                )
            )
        )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.body.decode("utf-8"))
        self.assertTrue(body["success"])

        saved = self._read_config()
        self.assertEqual(saved["ntrip"]["host"], "new-caster.example.com")
        self.assertEqual(saved["ntrip"]["password"], "super-secret")


if __name__ == "__main__":
    unittest.main()
