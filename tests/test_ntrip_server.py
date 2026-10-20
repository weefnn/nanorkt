import unittest

from app.drivers.ntrip_server import NTRIPServer


class NtripServerRequestFormatTests(unittest.TestCase):
    def test_source_request_has_single_header_terminator(self) -> None:
        server = NTRIPServer(
            host="caster.example.com",
            port=2101,
            mountpoint="RTCM32",
            username="user",
            password="pass",
        )

        request = server._build_source_request()

        self.assertEqual(request.count("\r\n\r\n"), 1)
        self.assertIn("Authorization: Basic", request)
        self.assertLess(
            request.index("Authorization: Basic"),
            request.index("\r\n\r\n"),
        )

    def test_source_request_without_credentials_has_no_auth_header(self) -> None:
        server = NTRIPServer(
            host="caster.example.com",
            port=2101,
            mountpoint="RTCM32",
            username="",
            password="",
        )

        request = server._build_source_request()

        self.assertNotIn("Authorization: Basic", request)
        self.assertEqual(request.count("\r\n\r\n"), 1)


if __name__ == "__main__":
    unittest.main()
