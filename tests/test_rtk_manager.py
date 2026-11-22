import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


_FAKE_APP = types.ModuleType("app")
_FAKE_APP.__path__ = []
_FAKE_CORE = types.ModuleType("app.core")
_FAKE_CORE.__path__ = []
_FAKE_STATION = types.ModuleType("app.core.station")


class _PlaceholderStation:
    def start(self):
        return True

    def stop(self):
        return None

    def get_status(self):
        return {}


_FAKE_STATION.RTKBaseStation = _PlaceholderStation
sys.modules.setdefault("app", _FAKE_APP)
sys.modules.setdefault("app.core", _FAKE_CORE)
sys.modules["app.core.station"] = _FAKE_STATION


_MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "web" / "services" / "rtk_manager.py"
)
_SPEC = importlib.util.spec_from_file_location("rtk_manager_under_test", _MODULE_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None and _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)


class _ImmediateThread:
    def __init__(self, target=None, name=None, daemon=None):
        self._target = target
        self._alive = False

    def start(self):
        self._alive = True
        try:
            if self._target:
                self._target()
        finally:
            self._alive = False

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        return None


class _FailFastStation:
    def start(self):
        return False

    def stop(self):
        return None

    def get_status(self):
        return {}


class RTKManagerRaceTests(unittest.TestCase):
    def test_start_service_does_not_leave_stale_running_state(self):
        manager = _MODULE.RTKManager()

        with patch.object(_MODULE, "RTKBaseStation", return_value=_FailFastStation()):
            with patch.object(_MODULE.threading, "Thread", _ImmediateThread):
                started = manager.start_service()

        self.assertTrue(started)
        self.assertFalse(manager.is_running())
        status = manager.get_status()
        self.assertFalse(status["running"])
        self.assertFalse(status["thread_alive"])


if __name__ == "__main__":
    unittest.main()
