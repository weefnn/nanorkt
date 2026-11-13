import unittest
from unittest.mock import Mock, patch

from app.drivers.qianxun import QianxunInitializer


class _FakeSerial:
    def __init__(self):
        self.in_waiting = 0

    def write(self, data: bytes) -> None:
        _ = data

    def flush(self) -> None:
        return None

    def read(self, size: int) -> bytes:
        _ = size
        return b""


class TestQianxunInitializer(unittest.TestCase):
    def setUp(self) -> None:
        self.initializer = QianxunInitializer(_FakeSerial())

    @patch("app.drivers.qianxun.time.sleep", return_value=None)
    def test_configure_rtcm_output_uses_configured_baudrate(self, _sleep_mock: Mock) -> None:
        sent_commands = []

        def _record_command(command: str, *args, **kwargs) -> bool:
            _ = (args, kwargs)
            sent_commands.append(command)
            return True

        self.initializer.send_command = _record_command  # type: ignore[assignment]

        ok = self.initializer.configure_rtcm_output(rate=1, baudrate=460800)

        self.assertTrue(ok)
        self.assertIn(
            "QXCFGPRT,0,0,,460800,h00000005,h00000004",
            sent_commands,
        )

    @patch("app.drivers.qianxun.time.sleep", return_value=None)
    def test_initialize_forwards_baudrate_to_rtcm_output(self, _sleep_mock: Mock) -> None:
        self.initializer.configure_baudrate = Mock(return_value=True)  # type: ignore[method-assign]
        self.initializer.configure_base_station_coordinates = Mock(return_value=True)  # type: ignore[method-assign]
        self.initializer.configure_rtcm_output = Mock(return_value=True)  # type: ignore[method-assign]

        ok = self.initializer.initialize(
            baudrate=57600,
            rtcm_rate=1,
            base_station_config={
                "latitude": 39.9,
                "longitude": 116.4,
                "altitude": 50.0,
                "enable_arp_average": 0,
            },
        )

        self.assertTrue(ok)
        self.initializer.configure_rtcm_output.assert_called_once_with(1, baudrate=57600)


if __name__ == "__main__":
    unittest.main()
