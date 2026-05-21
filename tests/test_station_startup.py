import unittest
from unittest.mock import MagicMock, patch

from app.core.exceptions import ReceiverInitError
from app.core.station import RTKBaseStation


class RTKBaseStationStartupTests(unittest.TestCase):
    def test_start_releases_resources_when_receiver_init_raises(self) -> None:
        station = RTKBaseStation()
        fake_serial_reader = MagicMock()
        station.serial_reader = fake_serial_reader

        with (
            patch.object(station, "setup_serial", return_value=True),
            patch.object(
                station,
                "initialize_receiver",
                side_effect=ReceiverInitError("init failed"),
            ),
            patch.object(station, "setup_ntrip") as setup_ntrip_mock,
        ):
            result = station.start()

        self.assertFalse(result)
        setup_ntrip_mock.assert_not_called()
        fake_serial_reader.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
