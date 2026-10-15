import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _load_ntrip_server_class():
    """直接按文件加载模块，避免依赖未安装时触发 package 级导入副作用。"""
    repo_root = Path(__file__).resolve().parents[1]
    exceptions_path = repo_root / "app" / "core" / "exceptions.py"
    ntrip_path = repo_root / "app" / "drivers" / "ntrip_server.py"

    app_pkg = sys.modules.setdefault("app", types.ModuleType("app"))
    app_pkg.__path__ = [str(repo_root / "app")]

    core_pkg = sys.modules.setdefault("app.core", types.ModuleType("app.core"))
    core_pkg.__path__ = [str(repo_root / "app" / "core")]

    exc_spec = importlib.util.spec_from_file_location("app.core.exceptions", exceptions_path)
    exc_module = importlib.util.module_from_spec(exc_spec)
    assert exc_spec.loader is not None
    exc_spec.loader.exec_module(exc_module)
    sys.modules["app.core.exceptions"] = exc_module

    ntrip_spec = importlib.util.spec_from_file_location("ntrip_server_under_test", ntrip_path)
    ntrip_module = importlib.util.module_from_spec(ntrip_spec)
    assert ntrip_spec.loader is not None
    ntrip_spec.loader.exec_module(ntrip_module)
    return ntrip_module.NTRIPServer


NTRIPServer = _load_ntrip_server_class()


class TestNtripSourceRequest(unittest.TestCase):
    def test_source_request_uses_single_header_terminator_with_auth(self):
        server = NTRIPServer(
            host="caster.example.com",
            port=2101,
            mountpoint="RTCM32",
            username="user",
            password="pass",
        )

        request = server._build_source_request()

        self.assertEqual(request.count("\r\n\r\n"), 1)
        header_end = request.index("\r\n\r\n")
        self.assertIn("Authorization: Basic ", request[:header_end])
        self.assertNotIn("Authorization: Basic ", request[header_end + 4 :])

    def test_source_request_omits_auth_when_credentials_missing(self):
        server = NTRIPServer(
            host="caster.example.com",
            port=2101,
            mountpoint="RTCM32",
            username="",
            password="",
        )

        request = server._build_source_request()
        self.assertNotIn("Authorization: Basic ", request)


if __name__ == "__main__":
    unittest.main()
