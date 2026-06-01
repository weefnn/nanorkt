import importlib.util
import sys
import types
import unittest
from pathlib import Path


def load_ntrip_server_class():
    # 注入最小依赖，避免测试环境必须安装完整运行时依赖。
    app_module = types.ModuleType("app")
    core_module = types.ModuleType("app.core")
    exceptions_module = types.ModuleType("app.core.exceptions")

    class NTRIPConnectionError(Exception):
        pass

    exceptions_module.NTRIPConnectionError = NTRIPConnectionError
    sys.modules.setdefault("app", app_module)
    sys.modules["app.core"] = core_module
    sys.modules["app.core.exceptions"] = exceptions_module

    module_path = Path(__file__).resolve().parents[1] / "app" / "drivers" / "ntrip_server.py"
    spec = importlib.util.spec_from_file_location("ntrip_server_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.NTRIPServer


NTRIPServer = load_ntrip_server_class()


class TestNtripSourceRequest(unittest.TestCase):
    def test_source_request_has_single_header_terminator(self):
        server = NTRIPServer(
            host="caster.example.com",
            port=2101,
            mountpoint="RTCM32",
            username="demo",
            password="secret",
        )
        request = server._build_source_request()

        # 头部与请求体分隔符只能出现一次，且必须在末尾。
        self.assertEqual(request.count("\r\n\r\n"), 1)
        header_part, body = request.split("\r\n\r\n", 1)
        self.assertEqual(body, "")

        self.assertTrue(header_part.startswith("SOURCE secret /RTCM32"))
        self.assertIn("Source-Agent: NanoRTK/2.0", header_part)
        self.assertIn("User-Agent: NanoRTK/2.0", header_part)
        self.assertIn("Authorization: Basic", header_part)

    def test_source_request_omits_authorization_without_credentials(self):
        server = NTRIPServer(
            host="caster.example.com",
            port=2101,
            mountpoint="RTCM32",
            username="",
            password="",
        )
        request = server._build_source_request()
        header_part, _ = request.split("\r\n\r\n", 1)

        self.assertNotIn("Authorization: Basic", header_part)


if __name__ == "__main__":
    unittest.main()
