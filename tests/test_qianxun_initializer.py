import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# 让测试在未安装 pyserial 的环境下也能导入驱动模块
sys.modules.setdefault(
    "serial",
    types.SimpleNamespace(Serial=object, SerialException=Exception),
)

# 避免导入 app.core.__init__（其依赖 pydantic），仅提供 qianxun 所需异常
app_module = sys.modules.setdefault("app", types.ModuleType("app"))
core_module = sys.modules.setdefault("app.core", types.ModuleType("app.core"))
exceptions_module = types.ModuleType("app.core.exceptions")


class ReceiverInitError(Exception):
    pass


exceptions_module.ReceiverInitError = ReceiverInitError
sys.modules["app.core.exceptions"] = exceptions_module
setattr(core_module, "exceptions", exceptions_module)
setattr(app_module, "core", core_module)

module_path = Path(__file__).resolve().parents[1] / "app" / "drivers" / "qianxun.py"
module_name = "qianxun_under_test"
module_spec = importlib.util.spec_from_file_location(module_name, module_path)
qianxun_module = importlib.util.module_from_spec(module_spec)
sys.modules[module_name] = qianxun_module
assert module_spec is not None and module_spec.loader is not None
module_spec.loader.exec_module(qianxun_module)
QianxunInitializer = qianxun_module.QianxunInitializer


class _FakeSerial:
    def __init__(self):
        self.writes = []
        self.in_waiting = 0

    def write(self, data: bytes):
        self.writes.append(data)

    def flush(self):
        return None

    def read(self, _size: int) -> bytes:
        return b""


class QianxunInitializerTests(unittest.TestCase):
    @patch.object(QianxunInitializer, "_wait_for_response", return_value=True)
    def test_configure_rtcm_output_uses_selected_baudrate(self, _mock_wait):
        serial_port = _FakeSerial()
        initializer = QianxunInitializer(serial_port)

        with patch.object(qianxun_module.time, "sleep", return_value=None):
            ok = initializer.configure_rtcm_output(rate=1, baudrate=230400)

        self.assertTrue(ok)
        commands = [data.decode("utf-8").strip() for data in serial_port.writes]
        self.assertIn(
            "$QXCFGPRT,0,0,,230400,h00000005,h00000004",
            commands,
            "端口配置命令应使用当前配置的波特率",
        )

    @patch.object(QianxunInitializer, "configure_rtcm_output", return_value=True)
    @patch.object(QianxunInitializer, "configure_base_station_coordinates", return_value=True)
    @patch.object(QianxunInitializer, "configure_baudrate", return_value=True)
    def test_initialize_passes_baudrate_to_rtcm_output(
        self,
        _mock_cfg_baud,
        _mock_cfg_coord,
        mock_cfg_rtcm,
    ):
        serial_port = _FakeSerial()
        initializer = QianxunInitializer(serial_port)

        with patch.object(qianxun_module.time, "sleep", return_value=None):
            ok = initializer.initialize(
                baudrate=460800,
                rtcm_rate=1,
                base_station_config={
                    "latitude": 30.0,
                    "longitude": 120.0,
                    "altitude": 10.0,
                    "enable_arp_average": 0,
                },
            )

        self.assertTrue(ok)
        mock_cfg_rtcm.assert_called_once_with(1, 460800)


if __name__ == "__main__":
    unittest.main()
