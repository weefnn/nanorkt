import base64
import unittest

from app.drivers.ntrip_server import NTRIPServer


class TestNTRIPSourceRequest(unittest.TestCase):
    def test_source_request_keeps_headers_in_single_block(self) -> None:
        server = NTRIPServer(
            host="caster.example.com",
            port=2101,
            mountpoint="RTCM32",
            username="user",
            password="pass",
        )

        request = server._build_source_request()

        self.assertEqual(request.count("\r\n\r\n"), 1)
        self.assertNotIn("Source-Agent: NanoRTK/2.0\r\n\r\nUser-Agent", request)

    def test_authorization_header_is_before_header_terminator(self) -> None:
        server = NTRIPServer(
            host="caster.example.com",
            port=2101,
            mountpoint="RTCM32",
            username="demo-user",
            password="demo-pass",
        )

        request = server._build_source_request()
        expected_token = base64.b64encode(b"demo-user:demo-pass").decode("utf-8")
        auth_line = f"Authorization: Basic {expected_token}\r\n"

        header_end_index = request.index("\r\n\r\n")
        auth_index = request.index(auth_line)

        self.assertLess(auth_index, header_end_index)


if __name__ == "__main__":
    unittest.main()
