import os
import unittest

from fastapi import HTTPException

from app.web.routes.api import (
    PASSWORD_MASK,
    _mask_sensitive_config,
    _preserve_masked_password,
)
from app.web.security import ensure_api_access


class FakeConfig:
    def get(self, key, default=None):
        current = {
            "ntrip": {"password": "real-secret"},
        }
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current


class FakeClient:
    def __init__(self, host):
        self.host = host


class FakeRequest:
    def __init__(self, host, headers=None):
        self.client = FakeClient(host)
        self.headers = headers or {}


class ApiSecurityTests(unittest.TestCase):
    def setUp(self):
        os.environ["NANORKT_ADMIN_TOKEN"] = "token-123"

    def tearDown(self):
        os.environ.pop("NANORKT_ADMIN_TOKEN", None)

    def test_remote_request_requires_token(self):
        denied_request = FakeRequest(host="203.0.113.2", headers={})
        with self.assertRaises(HTTPException):
            ensure_api_access(denied_request)

        allowed_request = FakeRequest(
            host="203.0.113.2",
            headers={"X-Admin-Token": "token-123"},
        )
        ensure_api_access(allowed_request)

    def test_masked_password_helpers(self):
        masked = _mask_sensitive_config(
            {"ntrip": {"host": "example.com", "password": "real-secret"}}
        )
        self.assertEqual(masked["ntrip"]["password"], PASSWORD_MASK)

        preserved = _preserve_masked_password(
            {"ntrip": {"password": PASSWORD_MASK}},
            FakeConfig(),
        )
        self.assertEqual(
            preserved["ntrip"]["password"],
            "real-secret",
        )


if __name__ == "__main__":
    unittest.main()
