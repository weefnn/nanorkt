import os
import tempfile
import unittest
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.web import create_app
from app.web.security import MASKED_PASSWORD


class ApiSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_cwd = os.getcwd()
        self._old_token = os.environ.get("NANORKT_ADMIN_TOKEN")
        os.environ["NANORKT_ADMIN_TOKEN"] = "test-token"

        self._temp_dir = tempfile.TemporaryDirectory()
        os.chdir(self._temp_dir.name)
        Path("config.yaml").write_text(
            yaml.safe_dump(
                {
                    "serial": {"port": "/dev/ttyUSB0", "baudrate": 115200},
                    "ntrip": {
                        "host": "example.com",
                        "port": 2101,
                        "mountpoint": "RTCM32",
                        "username": "demo",
                        "password": "super-secret",
                    },
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        os.chdir(self._old_cwd)
        self._temp_dir.cleanup()

        if self._old_token is None:
            os.environ.pop("NANORKT_ADMIN_TOKEN", None)
        else:
            os.environ["NANORKT_ADMIN_TOKEN"] = self._old_token

    def test_remote_request_without_token_is_rejected(self) -> None:
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 401)

    def test_control_endpoint_requires_token(self) -> None:
        response = self.client.post("/api/control", json={"action": "start"})
        self.assertEqual(response.status_code, 401)

    def test_config_password_is_masked(self) -> None:
        response = self.client.get(
            "/api/config",
            headers={"X-Admin-Token": "test-token"},
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["ntrip"]["password"], MASKED_PASSWORD)

    def test_masked_password_does_not_overwrite_saved_password(self) -> None:
        response = self.client.post(
            "/api/config",
            headers={"X-Admin-Token": "test-token"},
            json={
                "ntrip": {
                    "host": "new.example.com",
                    "password": MASKED_PASSWORD,
                }
            },
        )
        self.assertEqual(response.status_code, 200)

        updated = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
        self.assertEqual(updated["ntrip"]["host"], "new.example.com")
        self.assertEqual(updated["ntrip"]["password"], "super-secret")


if __name__ == "__main__":
    unittest.main()
