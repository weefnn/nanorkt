import threading
import time
import unittest

import app.web.services.rtk_manager as rtk_manager_module
from app.web.services.rtk_manager import RTKManager


class _DummyStation:
    started_count = 0
    stopped_count = 0
    _counter_lock = threading.Lock()
    _stop_event = threading.Event()

    def __init__(self):
        pass

    @classmethod
    def reset(cls) -> None:
        with cls._counter_lock:
            cls.started_count = 0
            cls.stopped_count = 0
        cls._stop_event = threading.Event()

    def start(self) -> bool:
        with self._counter_lock:
            self.__class__.started_count += 1
        # 保持运行一段时间，放大并发 start 的竞争窗口
        self.__class__._stop_event.wait(timeout=0.3)
        return True

    def stop(self) -> None:
        with self._counter_lock:
            self.__class__.stopped_count += 1
        self.__class__._stop_event.set()

    def get_status(self) -> dict:
        return {"dummy": True}


class RTKManagerConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_station_class = rtk_manager_module.RTKBaseStation
        _DummyStation.reset()
        rtk_manager_module.RTKBaseStation = _DummyStation

    def tearDown(self) -> None:
        rtk_manager_module.RTKBaseStation = self.original_station_class

    def test_concurrent_start_allows_only_one_success(self) -> None:
        manager = RTKManager()
        barrier = threading.Barrier(3)
        results = []

        def worker() -> None:
            barrier.wait()
            results.append(manager.start_service())

        thread_a = threading.Thread(target=worker)
        thread_b = threading.Thread(target=worker)
        thread_a.start()
        thread_b.start()

        barrier.wait()
        thread_a.join()
        thread_b.join()

        self.assertEqual(results.count(True), 1, results)
        self.assertEqual(results.count(False), 1, results)
        self.assertEqual(_DummyStation.started_count, 1)

        # 清理后台线程，避免影响其他测试
        if manager.is_running():
            self.assertTrue(manager.stop_service())
            time.sleep(0.05)


if __name__ == "__main__":
    unittest.main()
