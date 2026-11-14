import unittest
from unittest.mock import patch

from app.web.services.rtk_manager import RTKManager


class ImmediateExitStation:
    def start(self):
        return None

    def stop(self):
        return None

    def get_status(self):
        return {}


class FakeThread:
    def __init__(self, target=None, args=(), name=None, daemon=None):
        self._target = target
        self._args = args
        self._alive = False

    def start(self):
        self._alive = True
        if self._target:
            self._target(*self._args)
        self._alive = False

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        return None


class RTKManagerTests(unittest.TestCase):
    @patch("app.web.services.rtk_manager.RTKBaseStation", return_value=ImmediateExitStation())
    @patch("app.web.services.rtk_manager.threading.Thread", FakeThread)
    def test_start_service_does_not_leave_stale_running_when_worker_exits_immediately(self, _):
        manager = RTKManager()
        started = manager.start_service()
        self.assertTrue(started)
        self.assertFalse(manager.is_running())


if __name__ == "__main__":
    unittest.main()
