import importlib.util
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "web" / "services" / "rtk_manager.py"
SPEC = importlib.util.spec_from_file_location("rtk_manager_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("无法加载 rtk_manager 模块用于测试")


class _FakeStation:
    def start(self):
        return None

    def stop(self):
        return None

    def get_status(self):
        return {}


# 注入最小依赖，避免加载整套运行时依赖（fastapi/pydantic）
fake_app = sys.modules.setdefault("app", types.ModuleType("app"))
fake_core = sys.modules.setdefault("app.core", types.ModuleType("app.core"))
fake_station_module = types.ModuleType("app.core.station")
fake_station_module.RTKBaseStation = _FakeStation
sys.modules["app.core.station"] = fake_station_module
fake_app.core = fake_core
fake_core.station = fake_station_module

rtk_manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rtk_manager)
RTKManager = rtk_manager.RTKManager


class RTKManagerConcurrencyTest(unittest.TestCase):
    def test_start_service_prevents_concurrent_double_start(self):
        manager = RTKManager()
        real_thread_cls = threading.Thread
        release_start = threading.Event()
        first_thread_start_called = threading.Event()
        created_stations = []

        def station_factory():
            station = mock.Mock()
            created_stations.append(station)
            return station

        class BlockingThread:
            def __init__(self, target=None, args=(), name=None, daemon=None):
                self.target = target
                self.args = args
                self.name = name
                self.daemon = daemon

            def start(self):
                first_thread_start_called.set()
                # 阻塞第一个 start_service，使第二次 start 在其返回前触发
                release_start.wait(timeout=2)

            def is_alive(self):
                return False

            def join(self, timeout=None):
                return None

        with mock.patch.object(
            rtk_manager,
            "RTKBaseStation",
            side_effect=station_factory,
        ), mock.patch.object(
            rtk_manager.threading,
            "Thread",
            BlockingThread,
        ):
            first_result = {}

            def run_first_start():
                first_result["value"] = manager.start_service()

            first_start_thread = real_thread_cls(target=run_first_start)
            first_start_thread.start()

            self.assertTrue(first_thread_start_called.wait(timeout=1))
            second_result = manager.start_service()

            release_start.set()
            first_start_thread.join(timeout=1)

        self.assertTrue(first_result.get("value"))
        self.assertFalse(second_result)
        self.assertEqual(len(created_stations), 1)


if __name__ == "__main__":
    unittest.main()
