import unittest
from unittest.mock import patch

from app.web.services.rtk_manager import RTKManager


class _FastFailStation:
    def start(self):
        return False

    def stop(self):
        return None

    def get_status(self):
        return {"is_running": False}


class _ImmediateThread:
    def __init__(self, target, name=None, daemon=None):
        self._target = target
        self._alive = False

    def start(self):
        self._alive = True
        try:
            self._target()
        finally:
            self._alive = False

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        return None


class RTKManagerRaceConditionTest(unittest.TestCase):
    def test_start_service_fast_fail_does_not_leave_running_true(self):
        manager = RTKManager()

        with patch("app.web.services.rtk_manager.RTKBaseStation", _FastFailStation):
            with patch("app.web.services.rtk_manager.threading.Thread", _ImmediateThread):
                started = manager.start_service()

        self.assertTrue(started)
        self.assertFalse(manager.is_running())
        status = manager.get_status()
        self.assertFalse(status["running"])
        self.assertFalse(status["thread_alive"])


if __name__ == "__main__":
    unittest.main()
