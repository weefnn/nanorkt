import threading
import time
import unittest
from unittest import mock

from app.web.services.rtk_manager import RTKManager


class _FakeStation:
    instances = []
    release_event = threading.Event()

    def __init__(self):
        self.started = threading.Event()
        self.stopped = threading.Event()
        _FakeStation.instances.append(self)

    def start(self):
        self.started.set()
        _FakeStation.release_event.wait(timeout=3)

    def stop(self):
        self.stopped.set()
        _FakeStation.release_event.set()


class RTKManagerConcurrencyTests(unittest.TestCase):
    def setUp(self):
        _FakeStation.instances.clear()
        _FakeStation.release_event = threading.Event()

    def tearDown(self):
        _FakeStation.release_event.set()

    @mock.patch("app.web.services.rtk_manager.RTKBaseStation", _FakeStation)
    def test_concurrent_start_only_creates_one_station(self):
        manager = RTKManager()
        barrier = threading.Barrier(6)
        results = []
        results_lock = threading.Lock()

        def worker():
            barrier.wait()
            started = manager.start_service()
            with results_lock:
                results.append(started)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sum(results), 1, "并发启动应只允许一次成功")
        self.assertEqual(len(_FakeStation.instances), 1, "不应创建多余的基站实例")

        manager.stop_service()
        time.sleep(0.05)
        self.assertFalse(manager.is_running())

    @mock.patch("app.web.services.rtk_manager.RTKBaseStation", _FakeStation)
    def test_stop_service_stops_running_station(self):
        manager = RTKManager()
        self.assertTrue(manager.start_service())

        deadline = time.time() + 1.0
        while not _FakeStation.instances and time.time() < deadline:
            time.sleep(0.01)
        self.assertTrue(_FakeStation.instances, "启动后应创建基站实例")

        station = _FakeStation.instances[0]
        self.assertTrue(station.started.wait(timeout=1.0), "基站线程应开始运行")
        self.assertTrue(manager.stop_service(), "停止服务应返回成功")
        self.assertTrue(station.stopped.is_set(), "停止服务应调用 station.stop()")
        self.assertFalse(manager.is_running(), "停止后服务状态应为未运行")


if __name__ == "__main__":
    unittest.main()
