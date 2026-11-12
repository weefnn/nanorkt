import unittest
from unittest.mock import patch

from app.web.services.rtk_manager import RTKManager


class _ImmediateThread:
    def __init__(self, target=None, args=(), name=None, daemon=None):
        self._target = target
        self._args = args
        self._alive = False

    def start(self):
        self._alive = True
        try:
            if self._target:
                self._target(*self._args)
        finally:
            self._alive = False

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        return None


class _ImmediateExitStation:
    def start(self):
        return False

    def stop(self):
        return None

    def get_status(self):
        return {}


class RTKManagerTests(unittest.TestCase):
    def test_no_stale_running_flag_when_worker_exits_immediately(self):
        manager = RTKManager()

        with patch("app.web.services.rtk_manager.threading.Thread", _ImmediateThread):
            with patch("app.web.services.rtk_manager.RTKBaseStation", _ImmediateExitStation):
                started = manager.start_service()

        self.assertTrue(started)
        self.assertFalse(manager.is_running())


if __name__ == "__main__":
    unittest.main()
