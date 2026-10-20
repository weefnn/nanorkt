import sys
import types
import unittest
from unittest.mock import Mock, patch


serial_stub = types.ModuleType("serial")


class _SerialException(Exception):
    pass


class _Serial:
    pass


serial_stub.SerialException = _SerialException
serial_stub.Serial = _Serial
sys.modules.setdefault("serial", serial_stub)

from app.drivers.qianxun import QianxunInitializer


class QianxunInitializerTests(unittest.TestCase):
    def test_configure_rtcm_output_uses_requested_baudrate(self) -> None:
        initializer = QianxunInitializer(Mock())
        commands = []

        def fake_send_command(command: str, wait_response: bool = True, timeout: float = 2.0) -> bool:
            del wait_response, timeout
            commands.append(command)
            return True

        initializer.send_command = fake_send_command  # type: ignore[method-assign]

        with patch("app.drivers.qianxun.time.sleep", return_value=None):
            success = initializer.configure_rtcm_output(rate=1, baudrate=9600)

        self.assertTrue(success)
        self.assertEqual(
            commands[-1],
            "QXCFGPRT,0,0,,9600,h00000005,h00000004",
        )

    def test_initialize_passes_baudrate_to_rtcm_output(self) -> None:
        initializer = QianxunInitializer(Mock())
        initializer.configure_baudrate = Mock(return_value=True)  # type: ignore[method-assign]
        initializer.configure_rtcm_output = Mock(return_value=True)  # type: ignore[method-assign]

        with patch("app.drivers.qianxun.time.sleep", return_value=None):
            success = initializer.initialize(baudrate=57600, rtcm_rate=2, base_station_config=None)

        self.assertTrue(success)
        initializer.configure_baudrate.assert_called_once_with(57600)
        initializer.configure_rtcm_output.assert_called_once_with(2, baudrate=57600)


if __name__ == "__main__":
    unittest.main()
