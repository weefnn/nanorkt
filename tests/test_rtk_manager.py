import threading
import unittest
from unittest.mock import patch

from app.web.services.rtk_manager import RTKManager


class FakeStation:
    def __init__(
        self,
        started_event: threading.Event,
        release_event: threading.Event,
        *,
        stop_releases: bool,
    ):
        self.started_event = started_event
        self.release_event = release_event
        self.stop_releases = stop_releases

    def start(self) -> None:
        self.started_event.set()
        self.release_event.wait()

    def stop(self) -> None:
        if self.stop_releases:
            self.release_event.set()


class RTKManagerConcurrencyTest(unittest.TestCase):
    def test_stale_thread_must_not_clear_new_service_state(self) -> None:
        manager = RTKManager()
        manager.STOP_TIMEOUT = 0.05

        first_started = threading.Event()
        first_release = threading.Event()
        second_started = threading.Event()
        second_release = threading.Event()

        first_station = FakeStation(
            first_started, first_release, stop_releases=False
        )
        second_station = FakeStation(
            second_started, second_release, stop_releases=True
        )

        with patch(
            "app.web.services.rtk_manager.RTKBaseStation",
            side_effect=[first_station, second_station],
        ):
            self.assertTrue(manager.start_service())
            self.assertTrue(first_started.wait(timeout=1.0))

            first_thread = manager.thread
            self.assertIsNotNone(first_thread)

            # 第一次 stop 超时返回，旧线程仍可能存活
            self.assertTrue(manager.stop_service())
            self.assertTrue(first_thread.is_alive())

            # 立刻重启服务，绑定到新的 station
            self.assertTrue(manager.start_service())
            self.assertTrue(second_started.wait(timeout=1.0))
            self.assertIs(manager.station, second_station)
            self.assertTrue(manager.is_running())

            # 旧线程稍后退出，不应覆盖新服务状态
            first_release.set()
            first_thread.join(timeout=1.0)
            self.assertFalse(first_thread.is_alive())

            self.assertTrue(manager.is_running())
            self.assertIs(manager.station, second_station)

            # 清理第二个线程，避免泄露后台线程
            self.assertTrue(manager.stop_service())
            second_release.set()


if __name__ == "__main__":
    unittest.main()
