import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.web.app import create_app
from app.web.security import ADMIN_TOKEN_ENV, ADMIN_TOKEN_HEADER


class ApiAccessControlTests(unittest.TestCase):
    def test_remote_request_without_token_is_rejected(self) -> None:
        with patch.dict(os.environ, {ADMIN_TOKEN_ENV: "demo-token"}):
            with TestClient(create_app()) as client:
                response = client.get("/api/config")

        self.assertEqual(response.status_code, 403)

    def test_remote_request_with_valid_token_is_allowed(self) -> None:
        with patch.dict(os.environ, {ADMIN_TOKEN_ENV: "demo-token"}):
            with TestClient(create_app()) as client:
                response = client.get(
                    "/api/config",
                    headers={ADMIN_TOKEN_HEADER: "demo-token"},
                )

        self.assertEqual(response.status_code, 200)

    def test_loopback_request_is_allowed_without_token(self) -> None:
        with patch.dict(os.environ, {ADMIN_TOKEN_ENV: ""}):
            with patch("app.web.security._is_loopback_client", return_value=True):
                with TestClient(create_app()) as client:
                    response = client.get("/api/config")

        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
