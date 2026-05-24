import unittest
from unittest.mock import patch

from app.drivers.qianxun import QianxunInitializer


class DummySerial:
    def __init__(self):
        self.in_waiting = 0

    def write(self, _data: bytes) -> None:
        return None

    def flush(self) -> None:
        return None

    def read(self, _size: int) -> bytes:
        return b""


class RecordingInitializer(QianxunInitializer):
    def __init__(self):
        super().__init__(DummySerial())
        self.commands = []

    def send_command(self, command: str, wait_response: bool = True, timeout: float = 2.0) -> bool:
        self.commands.append(command)
        return True


class SpyInitializer(QianxunInitializer):
    def __init__(self):
        super().__init__(DummySerial())
        self.rtcm_call = None
        self.CONFIG_WAIT_TIME = 0

    def configure_baudrate(self, baudrate: int = 115200) -> bool:
        return True

    def configure_base_station_coordinates(
        self,
        latitude: float,
        longitude: float,
        altitude: float,
        enable_arp_average: int = 0,
    ) -> bool:
        return True

    def configure_rtcm_output(self, rate: int = 1, baudrate: int = 115200) -> bool:
        self.rtcm_call = (rate, baudrate)
        return True


class QianxunInitializerTests(unittest.TestCase):
    @patch("app.drivers.qianxun.time.sleep", return_value=None)
    def test_configure_rtcm_output_uses_requested_baudrate(self, _sleep_mock) -> None:
        initializer = RecordingInitializer()
        initializer.configure_rtcm_output(rate=1, baudrate=9600)

        self.assertIn("QXCFGPRT,0,0,,9600,h00000005,h00000004", initializer.commands)
        self.assertNotIn("QXCFGPRT,0,0,,115200,h00000005,h00000004", initializer.commands)

    @patch("app.drivers.qianxun.time.sleep", return_value=None)
    def test_initialize_passes_baudrate_into_rtcm_configuration(self, _sleep_mock) -> None:
        initializer = SpyInitializer()

        ok = initializer.initialize(baudrate=460800, rtcm_rate=2, base_station_config=None)

        self.assertTrue(ok)
        self.assertEqual((2, 460800), initializer.rtcm_call)


if __name__ == "__main__":
    unittest.main()
