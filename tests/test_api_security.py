import os
import tempfile
import unittest
import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import yaml
from fastapi import HTTPException
from starlette.requests import Request

from app.core.config import Config as CoreConfig
import app.web.routes.api as api_routes


class APISecurityTests(unittest.TestCase):
    def _write_config(self, path: Path, password: str = "real-secret") -> None:
        data = {
            "serial": {"port": "/dev/ttyUSB0", "baudrate": 115200},
            "ntrip": {
                "host": "caster.example.com",
                "port": 2101,
                "mountpoint": "MP1",
                "username": "u1",
                "password": password,
            },
            "reconnect": {"max_retries": 5, "retry_delay": 5.0},
            "base_station": {
                "latitude": 31.0,
                "longitude": 120.0,
                "altitude": 20.0,
                "enable_arp_average": 0,
            },
        }
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    def _config_factory(self, path: Path):
        return lambda: CoreConfig(str(path))

    def _make_request(
        self,
        method: str,
        path: str,
        headers: dict | None = None,
        client_host: str = "127.0.0.1",
        body: bytes = b"",
    ) -> Request:
        raw_headers = []
        if headers:
            for key, value in headers.items():
                raw_headers.append((key.lower().encode("utf-8"), value.encode("utf-8")))

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": raw_headers,
            "client": (client_host, 12345),
            "server": ("testserver", 8000),
            "scheme": "http",
        }

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        return Request(scope, receive)

    def test_remote_get_config_requires_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            self._write_config(config_path)

            with patch.object(api_routes, "Config", side_effect=self._config_factory(config_path)):
                with patch.dict(os.environ, {"NANORKT_ADMIN_TOKEN": "token-123"}, clear=False):
                    request = self._make_request(
                        "GET",
                        "/api/config",
                        headers={"x-forwarded-for": "192.168.1.20"},
                    )
                    with self.assertRaises(HTTPException) as ctx:
                        asyncio.run(api_routes.get_config(request))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_remote_get_config_masks_password_when_authorized(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            self._write_config(config_path, password="super-secret")

            with patch.object(api_routes, "Config", side_effect=self._config_factory(config_path)):
                with patch.dict(os.environ, {"NANORKT_ADMIN_TOKEN": "token-123"}, clear=False):
                    request = self._make_request(
                        "GET",
                        "/api/config",
                        headers={
                            "x-forwarded-for": "10.0.0.8",
                            "x-admin-token": "token-123",
                        },
                    )
                    result = asyncio.run(api_routes.get_config(request))

        self.assertEqual(result["ntrip"]["password"], "********")

    def test_masked_password_is_preserved_on_config_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            self._write_config(config_path, password="keep-me")

            with patch.object(api_routes, "Config", side_effect=self._config_factory(config_path)):
                with patch.dict(os.environ, {"NANORKT_ADMIN_TOKEN": "token-123"}, clear=False):
                    payload = json.dumps(
                        {
                            "ntrip.host": "new-caster.example.com",
                            "ntrip.password": "********",
                        }
                    ).encode("utf-8")
                    request = self._make_request(
                        "POST",
                        "/api/config",
                        headers={
                            "content-type": "application/json",
                            "x-forwarded-for": "10.0.0.8",
                            "x-admin-token": "token-123",
                        },
                        body=payload,
                    )
                    response = asyncio.run(api_routes.update_config(request))

            cfg = CoreConfig(str(config_path))
            ntrip = cfg.get_ntrip_config()
            response_body = json.loads(response.body.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response_body["success"])
        self.assertEqual(ntrip.host, "new-caster.example.com")
        self.assertEqual(ntrip.password, "keep-me")

    def test_remote_control_requires_token(self) -> None:
        with patch.dict(os.environ, {"NANORKT_ADMIN_TOKEN": "token-123"}, clear=False):
            payload = json.dumps({"action": "stop"}).encode("utf-8")
            request = self._make_request(
                "POST",
                "/api/control",
                headers={
                    "content-type": "application/json",
                    "x-forwarded-for": "203.0.113.10",
                },
                body=payload,
            )
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(api_routes.control_service(request))
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
