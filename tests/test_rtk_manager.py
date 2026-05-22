import importlib.util
import pathlib
import sys
import types
import unittest


ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
RTK_MANAGER_PATH = ROOT_DIR / "app" / "web" / "services" / "rtk_manager.py"


def load_rtk_manager_module():
    """在不依赖 FastAPI/Pydantic 的环境下加载 rtk_manager 模块。"""
    app_pkg = sys.modules.setdefault("app", types.ModuleType("app"))
    core_pkg = types.ModuleType("app.core")
    station_pkg = types.ModuleType("app.core.station")

    class StubStation:
        def start(self):
            return True

        def stop(self):
            return None

        def get_status(self):
            return {}

    station_pkg.RTKBaseStation = StubStation
    core_pkg.station = station_pkg
    app_pkg.core = core_pkg

    sys.modules["app.core"] = core_pkg
    sys.modules["app.core.station"] = station_pkg

    spec = importlib.util.spec_from_file_location("rtk_manager_under_test", RTK_MANAGER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ImmediateThread:
    """同步执行 target 的伪线程，用于稳定复现竞态。"""

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


class RTKManagerRaceConditionTests(unittest.TestCase):
    def test_start_service_keeps_stale_running_false_after_fast_failure(self):
        module = load_rtk_manager_module()
        module.threading.Thread = ImmediateThread

        class FastFailStation:
            def start(self):
                return False

            def stop(self):
                return None

            def get_status(self):
                return {"source": "fast-fail"}

        module.RTKBaseStation = FastFailStation

        manager = module.RTKManager()
        started = manager.start_service()

        self.assertTrue(started)
        self.assertFalse(manager.is_running())
        self.assertIsNone(manager.station)
        self.assertIsNone(manager.thread)
        self.assertEqual(
            manager.get_status(),
            {"running": False, "thread_alive": False},
        )


if __name__ == "__main__":
    unittest.main()
