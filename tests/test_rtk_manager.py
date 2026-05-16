import threading
import time
import unittest
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

app_module = types.ModuleType("app")
app_module.__path__ = []
core_module = types.ModuleType("app.core")
core_module.__path__ = []
station_module = types.ModuleType("app.core.station")


class _PlaceholderStation:
    def start(self):
        pass

    def stop(self):
        pass

    def get_status(self):
        return {}


station_module.RTKBaseStation = _PlaceholderStation

sys.modules.setdefault("app", app_module)
sys.modules.setdefault("app.core", core_module)
sys.modules["app.core.station"] = station_module

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "web" / "services" / "rtk_manager.py"
MODULE_SPEC = importlib.util.spec_from_file_location("rtk_manager_module_under_test", MODULE_PATH)
rtk_manager_module = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC.loader is not None
MODULE_SPEC.loader.exec_module(rtk_manager_module)


class SlowInitStation:
    created_count = 0
    created_lock = threading.Lock()

    def __init__(self):
        with self.created_lock:
            type(self).created_count += 1
        self._stop_event = threading.Event()
        # 放大并发窗口，确保测试能覆盖竞态路径
        time.sleep(0.05)

    def start(self):
        self._stop_event.wait(timeout=1.0)

    def stop(self):
        self._stop_event.set()

    def get_status(self):
        return {"station": "slow-init"}


class CoordinatedStation:
    created_count = 0
    created_lock = threading.Lock()
    first_started = threading.Event()
    first_stop_called = threading.Event()
    first_allow_exit = threading.Event()

    def __init__(self):
        with self.created_lock:
            type(self).created_count += 1
            self.instance_id = type(self).created_count
        self._stop_event = threading.Event()

    def start(self):
        if self.instance_id == 1:
            self.first_started.set()
            self._stop_event.wait(timeout=2.0)
            # 卡住第一个实例退出，制造 stop 与新 start 交错窗口
            self.first_allow_exit.wait(timeout=2.0)
        else:
            self._stop_event.wait(timeout=2.0)

    def stop(self):
        if self.instance_id == 1:
            self.first_stop_called.set()
        self._stop_event.set()

    def get_status(self):
        return {"station_id": self.instance_id}


class RTKManagerConcurrencyTest(unittest.TestCase):
    def setUp(self):
        rtk_manager_module.reset_manager()

    def tearDown(self):
        try:
            manager = rtk_manager_module.get_manager()
            if manager.is_running():
                manager.stop_service()
        finally:
            rtk_manager_module.reset_manager()

    def test_concurrent_start_only_creates_one_station(self):
        SlowInitStation.created_count = 0
        manager = rtk_manager_module.get_manager()
        start_gate = threading.Barrier(3)
        results = []
        results_lock = threading.Lock()

        def worker():
            start_gate.wait()
            result = manager.start_service()
            with results_lock:
                results.append(result)

        with patch.object(rtk_manager_module, "RTKBaseStation", SlowInitStation):
            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            start_gate.wait()
            t1.join(timeout=2.0)
            t2.join(timeout=2.0)

            self.assertEqual(results.count(True), 1)
            self.assertEqual(results.count(False), 1)
            self.assertEqual(SlowInitStation.created_count, 1)

            if manager.is_running():
                manager.stop_service()

    def test_stop_does_not_clear_newly_started_service(self):
        CoordinatedStation.created_count = 0
        CoordinatedStation.first_started.clear()
        CoordinatedStation.first_stop_called.clear()
        CoordinatedStation.first_allow_exit.clear()

        manager = rtk_manager_module.get_manager()

        with patch.object(rtk_manager_module, "RTKBaseStation", CoordinatedStation):
            self.assertTrue(manager.start_service())
            self.assertTrue(CoordinatedStation.first_started.wait(timeout=1.0))

            stop_done = threading.Event()

            def stop_worker():
                manager.stop_service()
                stop_done.set()

            t_stop = threading.Thread(target=stop_worker)
            t_stop.start()

            self.assertTrue(CoordinatedStation.first_stop_called.wait(timeout=1.0))

            # 在 stop 尚未完成时重新 start，验证不会被旧 stop 流程误清理
            self.assertTrue(manager.start_service())

            CoordinatedStation.first_allow_exit.set()
            self.assertTrue(stop_done.wait(timeout=2.0))
            t_stop.join(timeout=2.0)

            self.assertTrue(manager.is_running())
            self.assertIsNotNone(manager.station)
            self.assertEqual(manager.station.instance_id, 2)

            manager.stop_service()


if __name__ == "__main__":
    unittest.main()
