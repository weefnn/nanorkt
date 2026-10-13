import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from app.web.routes.api import ADMIN_TOKEN_ENV, _require_admin


def _build_request(host: str, headers=None, query: str = "") -> Request:
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("utf-8"), value.encode("utf-8")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/config",
        "headers": raw_headers,
        "query_string": query.encode("utf-8"),
        "client": (host, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


class AdminAuthGuardTest(unittest.TestCase):
    def test_local_request_allowed_without_token(self):
        request = _build_request("127.0.0.1")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ADMIN_TOKEN_ENV, None)
            _require_admin(request)

    def test_remote_request_rejected_without_token(self):
        request = _build_request("10.0.0.8")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ADMIN_TOKEN_ENV, None)
            with self.assertRaises(HTTPException) as ctx:
                _require_admin(request)
            self.assertEqual(ctx.exception.status_code, 403)

    def test_remote_request_allowed_with_header_token(self):
        request = _build_request("10.0.0.8", headers={"X-Admin-Token": "secret-token"})
        with patch.dict(os.environ, {ADMIN_TOKEN_ENV: "secret-token"}, clear=False):
            _require_admin(request)

    def test_remote_request_allowed_with_query_token(self):
        request = _build_request("10.0.0.8", query="token=query-secret")
        with patch.dict(os.environ, {ADMIN_TOKEN_ENV: "query-secret"}, clear=False):
            _require_admin(request)


if __name__ == "__main__":
    unittest.main()
