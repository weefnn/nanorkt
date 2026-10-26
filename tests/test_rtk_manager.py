import importlib.util
import sys
import time
import types
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "web" / "services" / "rtk_manager.py"


def load_manager_module(fake_station_cls):
    """加载 rtk_manager 模块，并注入可控的 RTKBaseStation 替身。"""
    app_mod = types.ModuleType("app")
    core_mod = types.ModuleType("app.core")
    station_mod = types.ModuleType("app.core.station")
    station_mod.RTKBaseStation = fake_station_cls

    module_name = f"rtk_manager_test_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)

    with mock.patch.dict(
        sys.modules,
        {
            "app": app_mod,
            "app.core": core_mod,
            "app.core.station": station_mod,
        },
        clear=False,
    ):
        spec.loader.exec_module(module)

    return module


class RTKManagerRaceTests(unittest.TestCase):
    def test_fast_exit_worker_should_not_leave_running_true(self):
        class FastFailStation:
            def start(self):
                return False

            def stop(self):
                return None

        mod = load_manager_module(FastFailStation)
        manager = mod.RTKManager()

        self.assertTrue(manager.start_service())

        deadline = time.time() + 0.5
        while time.time() < deadline and manager.is_running():
            time.sleep(0.001)

        status = manager.get_status()
        self.assertFalse(status["running"])
        self.assertFalse(status["thread_alive"])

    def test_can_start_again_after_fast_failure(self):
        class FastFailStation:
            def start(self):
                return False

            def stop(self):
                return None

        mod = load_manager_module(FastFailStation)
        manager = mod.RTKManager()

        self.assertTrue(manager.start_service())

        deadline = time.time() + 0.5
        while time.time() < deadline and manager.is_running():
            time.sleep(0.001)

        self.assertTrue(manager.start_service())


if __name__ == "__main__":
    unittest.main()
