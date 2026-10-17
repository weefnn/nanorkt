import os
import unittest

from fastapi import HTTPException
from starlette.requests import Request

from app.web.security import ensure_api_access


class ApiSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("NANORTK_API_TOKEN", None)

    def _build_request(self, client_host: str, headers: dict | None = None) -> Request:
        header_pairs = []
        if headers:
            header_pairs = [
                (key.lower().encode("utf-8"), value.encode("utf-8"))
                for key, value in headers.items()
            ]

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/config",
            "query_string": b"",
            "headers": header_pairs,
            "client": (client_host, 34567),
            "server": ("testserver", 80),
        }
        return Request(scope)

    def test_remote_access_without_token_is_denied(self) -> None:
        request = self._build_request("192.168.10.20")
        with self.assertRaises(HTTPException) as ctx:
            ensure_api_access(request)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access denied", str(ctx.exception.detail))

    def test_loopback_access_without_token_is_allowed(self) -> None:
        request = self._build_request("127.0.0.1")
        ensure_api_access(request)

    def test_remote_access_with_token_is_allowed(self) -> None:
        os.environ["NANORTK_API_TOKEN"] = "test-token"
        request = self._build_request(
            "192.168.10.20", headers={"X-API-Token": "test-token"}
        )
        ensure_api_access(request)


if __name__ == "__main__":
    unittest.main()
