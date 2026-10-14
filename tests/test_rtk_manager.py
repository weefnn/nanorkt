import importlib.util
import sys
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_rtk_manager_module():
    module_path = Path(__file__).resolve().parents[1] / "app" / "web" / "services" / "rtk_manager.py"

    fake_station_module = types.ModuleType("app.core.station")

    class PlaceholderStation:
        pass

    fake_station_module.RTKBaseStation = PlaceholderStation
    sys.modules["app.core.station"] = fake_station_module

    spec = importlib.util.spec_from_file_location("rtk_manager_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


RTK_MANAGER_MODULE = _load_rtk_manager_module()


class RTKManagerConcurrencyTest(unittest.TestCase):
    def test_concurrent_start_only_allows_one_service_thread(self) -> None:
        release_event = threading.Event()
        start_counter_lock = threading.Lock()

        class FakeStation:
            start_calls = 0

            def start(self) -> None:
                with start_counter_lock:
                    FakeStation.start_calls += 1
                release_event.wait(timeout=2.0)

            def stop(self) -> None:
                release_event.set()

            def get_status(self) -> dict:
                return {}

        manager = RTK_MANAGER_MODULE.RTKManager()
        barrier = threading.Barrier(2)
        results = []

        def start_worker() -> None:
            barrier.wait()
            results.append(manager.start_service())

        with patch.object(RTK_MANAGER_MODULE, "RTKBaseStation", FakeStation):
            t1 = threading.Thread(target=start_worker)
            t2 = threading.Thread(target=start_worker)
            t1.start()
            t2.start()
            t1.join(timeout=2.0)
            t2.join(timeout=2.0)

            self.assertEqual(results.count(True), 1)
            self.assertEqual(results.count(False), 1)

            # 等待后台线程执行到 FakeStation.start()
            deadline = time.time() + 1.0
            while time.time() < deadline and FakeStation.start_calls == 0:
                time.sleep(0.01)

            self.assertEqual(FakeStation.start_calls, 1)

            stopped = manager.stop_service()
            self.assertTrue(stopped)


if __name__ == "__main__":
    unittest.main()
