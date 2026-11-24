import unittest
from unittest.mock import patch
import importlib.util
from pathlib import Path
import sys
import types

# 提供最小依赖桩，避免测试依赖完整运行环境
serial_stub = types.ModuleType("serial")
serial_stub.Serial = object
serial_stub.SerialException = Exception
sys.modules.setdefault("serial", serial_stub)

app_stub = types.ModuleType("app")
app_stub.__path__ = []  # type: ignore[attr-defined]
core_stub = types.ModuleType("app.core")
core_stub.__path__ = []  # type: ignore[attr-defined]
exceptions_stub = types.ModuleType("app.core.exceptions")


class ReceiverInitError(Exception):
    pass


exceptions_stub.ReceiverInitError = ReceiverInitError
sys.modules.setdefault("app", app_stub)
sys.modules.setdefault("app.core", core_stub)
sys.modules.setdefault("app.core.exceptions", exceptions_stub)

module_path = Path(__file__).resolve().parents[1] / "app" / "drivers" / "qianxun.py"
spec = importlib.util.spec_from_file_location("nanorkt_qianxun", module_path)
qianxun_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(qianxun_module)
QianxunInitializer = qianxun_module.QianxunInitializer


class _DummySerial:
    def __init__(self):
        self.in_waiting = 0

    def write(self, _data: bytes) -> None:
        return None

    def flush(self) -> None:
        return None


class QianxunInitializerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.initializer = QianxunInitializer(_DummySerial())

    def test_configure_rtcm_output_uses_given_baudrate(self) -> None:
        commands = []

        def _record_command(command: str, *_args, **_kwargs) -> bool:
            commands.append(command)
            return True

        self.initializer.send_command = _record_command  # type: ignore[method-assign]

        with patch.object(qianxun_module.time, "sleep", return_value=None):
            success = self.initializer.configure_rtcm_output(rate=1, baudrate=460800)

        self.assertTrue(success)
        self.assertTrue(commands)
        self.assertEqual(
            commands[-1],
            "QXCFGPRT,0,0,,460800,h00000005,h00000004",
        )

    def test_initialize_passes_baudrate_to_rtcm_config(self) -> None:
        with patch.object(qianxun_module.time, "sleep", return_value=None):
            with (
                patch.object(self.initializer, "configure_baudrate", return_value=True),
                patch.object(
                    self.initializer, "configure_rtcm_output", return_value=True
                ) as mock_configure_rtcm,
            ):
                success = self.initializer.initialize(
                    baudrate=230400,
                    rtcm_rate=2,
                    base_station_config=None,
                )

        self.assertTrue(success)
        mock_configure_rtcm.assert_called_once_with(2, baudrate=230400)


if __name__ == "__main__":
    unittest.main()
