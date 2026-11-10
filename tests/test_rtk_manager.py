import importlib.util
import sys
import threading
import time
import types
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MANAGER_PATH = ROOT_DIR / "app" / "web" / "services" / "rtk_manager.py"


def load_manager_module():
    """在无第三方依赖环境下加载 rtk_manager。"""
    module_name = f"rtk_manager_test_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, MANAGER_PATH)
    module = importlib.util.module_from_spec(spec)

    fake_station_module = types.ModuleType("app.core.station")

    class PlaceholderStation:
        def start(self):
            return True

        def stop(self):
            return None

        def get_status(self):
            return {}

    fake_station_module.RTKBaseStation = PlaceholderStation
    previous_station_module = sys.modules.get("app.core.station")
    sys.modules["app.core.station"] = fake_station_module

    try:
        spec.loader.exec_module(module)
    finally:
        if previous_station_module is None:
            del sys.modules["app.core.station"]
        else:
            sys.modules["app.core.station"] = previous_station_module

    return module


class RTKManagerConcurrencyTests(unittest.TestCase):
    def test_no_stale_running_flag_when_worker_exits_immediately(self):
        module = load_manager_module()
        real_threading = threading

        class FakeStation:
            def start(self):
                return True

            def stop(self):
                return None

            def get_status(self):
                return {}

        class YieldingThread(real_threading.Thread):
            def start(self):
                super().start()
                # 放大旧实现中的时序问题：让 worker 先结束，再返回到 start_service。
                time.sleep(0.05)

        module.RTKBaseStation = FakeStation
        module.threading = types.SimpleNamespace(
            Thread=YieldingThread,
            Lock=real_threading.Lock,
            current_thread=real_threading.current_thread,
        )

        manager = module.RTKManager()
        self.assertTrue(manager.start_service())
        if manager.thread:
            manager.thread.join()
        self.assertFalse(manager.is_running())

    def test_start_service_prevents_concurrent_double_start(self):
        module = load_manager_module()
        real_threading = threading

        class FakeStation:
            def __init__(self):
                # 放大竞态窗口：无锁实现下两个并发 start 都可能通过检查。
                time.sleep(0.05)

            def start(self):
                return True

            def stop(self):
                return None

            def get_status(self):
                return {}

        class PassiveThread:
            def __init__(self, target=None, args=(), kwargs=None, name=None, daemon=None):
                self._alive = False

            def start(self):
                self._alive = True

            def is_alive(self):
                return self._alive

            def join(self, timeout=None):
                self._alive = False

        module.RTKBaseStation = FakeStation
        module.threading = types.SimpleNamespace(
            Thread=PassiveThread,
            Lock=real_threading.Lock,
            current_thread=real_threading.current_thread,
        )

        manager = module.RTKManager()
        results = []
        errors = []
        barrier = real_threading.Barrier(2)

        def call_start():
            try:
                barrier.wait()
                results.append(manager.start_service())
            except Exception as exc:  # pragma: no cover - 仅用于调试失败现场
                errors.append(exc)

        t1 = real_threading.Thread(target=call_start)
        t2 = real_threading.Thread(target=call_start)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(errors, [])
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 1)
        self.assertTrue(manager.stop_service())


if __name__ == "__main__":
    unittest.main()
