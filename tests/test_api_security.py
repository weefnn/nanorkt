import os
import unittest
import asyncio

from fastapi import HTTPException
from starlette.requests import Request

from app.web.routes.api import get_config
from app.web.security import ADMIN_TOKEN_ENV, ADMIN_TOKEN_HEADER, ensure_api_access


def _build_request(host: str, headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/config",
        "raw_path": b"/api/config",
        "query_string": b"",
        "headers": raw_headers,
        "client": (host, 50000),
        "server": ("testserver", 80),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


class EnsureApiAccessTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ADMIN_TOKEN_ENV, None)

    def test_loopback_request_allowed_without_token(self):
        request = _build_request("127.0.0.1")
        ensure_api_access(request)

    def test_remote_request_rejected_without_token(self):
        request = _build_request("8.8.8.8")
        with self.assertRaises(HTTPException) as exc:
            ensure_api_access(request)
        self.assertEqual(exc.exception.status_code, 403)

    def test_remote_request_allowed_with_valid_token(self):
        os.environ[ADMIN_TOKEN_ENV] = "secret-token"
        request = _build_request("8.8.8.8", {ADMIN_TOKEN_HEADER: "secret-token"})
        ensure_api_access(request)


class ApiRouteSecurityTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ADMIN_TOKEN_ENV, None)

    def test_config_endpoint_rejects_remote_without_token(self):
        request = _build_request("8.8.8.8")

        async def run_call():
            await get_config(request)

        with self.assertRaises(HTTPException) as exc:
            asyncio.run(run_call())
        self.assertEqual(exc.exception.status_code, 403)

    def test_config_endpoint_accepts_remote_with_token(self):
        os.environ[ADMIN_TOKEN_ENV] = "secret-token"
        request = _build_request("8.8.8.8", {ADMIN_TOKEN_HEADER: "secret-token"})

        async def run_call():
            return await get_config(request)

        result = asyncio.run(run_call())
        self.assertIn("serial", result)


if __name__ == "__main__":
    unittest.main()
