import sys
import types
import unittest

# 为测试环境注入最小 serial stub，避免依赖系统 pyserial 安装
serial_stub = types.ModuleType("serial")


class _SerialException(Exception):
    pass


class _Serial:
    pass


serial_stub.SerialException = _SerialException
serial_stub.Serial = _Serial
sys.modules.setdefault("serial", serial_stub)

from app.drivers.qianxun import QianxunInitializer


class _DummySerial:
    def write(self, _data: bytes) -> None:
        pass

    def flush(self) -> None:
        pass

    @property
    def in_waiting(self) -> int:
        return 0

    def read(self, _size: int) -> bytes:
        return b""


class QianxunInitializerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.initializer = QianxunInitializer(_DummySerial())

    def test_configure_rtcm_output_uses_configured_baudrate(self) -> None:
        commands = []

        def fake_send_command(command: str, *_args, **_kwargs) -> bool:
            commands.append(command)
            return True

        self.initializer.send_command = fake_send_command  # type: ignore[method-assign]
        ok = self.initializer.configure_rtcm_output(rate=1, baudrate=57600)

        self.assertTrue(ok)
        self.assertIn("QXCFGPRT,0,0,,57600,h00000005,h00000004", commands)

    def test_initialize_passes_baudrate_to_rtcm_output(self) -> None:
        called = {}

        self.initializer.configure_baudrate = lambda _baud: True  # type: ignore[method-assign]

        def fake_configure_rtcm_output(rate: int, baudrate: int = 115200) -> bool:
            called["rate"] = rate
            called["baudrate"] = baudrate
            return True

        self.initializer.configure_rtcm_output = fake_configure_rtcm_output  # type: ignore[method-assign]
        ok = self.initializer.initialize(baudrate=38400, rtcm_rate=2, base_station_config=None)

        self.assertTrue(ok)
        self.assertEqual(called["rate"], 2)
        self.assertEqual(called["baudrate"], 38400)


if __name__ == "__main__":
    unittest.main()
