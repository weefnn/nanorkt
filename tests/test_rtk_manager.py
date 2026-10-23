import importlib.util
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "app/web/services/rtk_manager.py"


class FakeStation:
    def start(self):
        return False

    def stop(self):
        return None

    def get_status(self):
        return {}


class ImmediateExitThread:
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


class FailingStartThread(ImmediateExitThread):
    def start(self):
        raise RuntimeError("thread start failed")


def load_rtk_manager_module():
    spec = importlib.util.spec_from_file_location("rtk_manager_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RTKManagerTest(unittest.TestCase):
    def setUp(self):
        self._original_modules = {}
        for name in ("app", "app.core", "app.core.station"):
            self._original_modules[name] = sys.modules.get(name)

        app_module = types.ModuleType("app")
        core_module = types.ModuleType("app.core")
        station_module = types.ModuleType("app.core.station")
        station_module.RTKBaseStation = FakeStation

        sys.modules["app"] = app_module
        sys.modules["app.core"] = core_module
        sys.modules["app.core.station"] = station_module

    def tearDown(self):
        for name, original in self._original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def test_start_service_not_stuck_running_after_immediate_thread_exit(self):
        module = load_rtk_manager_module()
        original_thread = module.threading.Thread
        module.threading.Thread = ImmediateExitThread
        try:
            manager = module.RTKManager()
            started = manager.start_service()

            self.assertTrue(started)
            self.assertFalse(manager.thread.is_alive())
            self.assertFalse(
                manager.is_running(),
                "线程已退出时，管理器不应残留 running=True",
            )
        finally:
            module.threading.Thread = original_thread

    def test_start_service_rolls_back_state_when_thread_fails_to_start(self):
        module = load_rtk_manager_module()
        original_thread = module.threading.Thread
        module.threading.Thread = FailingStartThread
        try:
            manager = module.RTKManager()
            started = manager.start_service()

            self.assertFalse(started)
            self.assertFalse(manager.is_running())
            self.assertIsNone(manager.station)
            self.assertIsNone(manager.thread)
        finally:
            module.threading.Thread = original_thread


if __name__ == "__main__":
    unittest.main()
