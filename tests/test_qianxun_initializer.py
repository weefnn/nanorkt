import unittest
from unittest.mock import MagicMock, patch

from app.drivers.qianxun import QianxunInitializer


class DummySerial:
    in_waiting = 0

    def write(self, _):
        return None

    def flush(self):
        return None

    def read(self, _):
        return b""


class QianxunInitializerTests(unittest.TestCase):
    def test_configure_rtcm_output_uses_configured_baudrate(self):
        initializer = QianxunInitializer(DummySerial())
        sent_commands = []
        initializer.send_command = lambda command, **kwargs: sent_commands.append(command) or True

        with patch("app.drivers.qianxun.time.sleep", return_value=None):
            success = initializer.configure_rtcm_output(rate=1, baudrate=460800)

        self.assertTrue(success)
        self.assertIn("QXCFGPRT,0,0,,460800,h00000005,h00000004", sent_commands)

    def test_initialize_passes_baudrate_to_rtcm_output(self):
        initializer = QianxunInitializer(DummySerial())
        initializer.configure_baudrate = MagicMock(return_value=True)
        initializer.configure_rtcm_output = MagicMock(return_value=True)

        with patch("app.drivers.qianxun.time.sleep", return_value=None):
            ok = initializer.initialize(baudrate=230400, rtcm_rate=2, base_station_config=None)

        self.assertTrue(ok)
        initializer.configure_rtcm_output.assert_called_once_with(2, baudrate=230400)


if __name__ == "__main__":
    unittest.main()
