import unittest

from app.drivers.ntrip_server import NTRIPServer


class NTRIPServerRequestTests(unittest.TestCase):
    def test_source_request_places_authorization_before_final_header_terminator(self) -> None:
        server = NTRIPServer(
            host="caster.example.com",
            port=2101,
            mountpoint="RTCM32",
            username="user",
            password="pass",
        )

        request = server._build_source_request()

        header_end = request.index("\r\n\r\n")
        authorization_line = "Authorization: Basic dXNlcjpwYXNz\r\n"

        self.assertIn(authorization_line, request)
        self.assertLess(
            request.index(authorization_line),
            header_end,
            "Authorization 必须位于 header 结束符之前",
        )
        self.assertEqual(
            request.count("\r\n\r\n"),
            1,
            "请求头只能有一个结束符，避免提前截断后续头字段",
        )


if __name__ == "__main__":
    unittest.main()
