import unittest
from unittest.mock import patch

from app.web.services.rtk_manager import RTKManager


class _FastExitStation:
    def start(self) -> bool:
        return False

    def stop(self) -> None:
        return None

    def get_status(self) -> dict:
        return {"mock": True}


class _ImmediateThread:
    def __init__(self, target, args=(), name=None, daemon=None):
        self._target = target
        self._args = args
        self._alive = False
        self.name = name
        self.daemon = daemon

    def start(self) -> None:
        self._alive = True
        try:
            self._target(*self._args)
        finally:
            self._alive = False

    def is_alive(self) -> bool:
        return self._alive

    def join(self, timeout=None) -> None:
        _ = timeout
        return None


class TestRTKManager(unittest.TestCase):
    @patch("app.web.services.rtk_manager.RTKBaseStation", _FastExitStation)
    @patch("app.web.services.rtk_manager.threading.Thread", _ImmediateThread)
    def test_no_stale_running_flag_when_worker_exits_immediately(self) -> None:
        manager = RTKManager()

        started = manager.start_service()

        self.assertTrue(started)
        self.assertFalse(
            manager.is_running(),
            "worker 秒退后不应残留 running=True 的假运行状态",
        )


if __name__ == "__main__":
    unittest.main()
