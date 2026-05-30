import threading
import time
import unittest
from unittest.mock import patch

from app.web.services.rtk_manager import RTKManager


class FakeStation:
    started_count = 0
    lock = threading.Lock()

    def __init__(self):
        # 拉长初始化窗口，稳定复现并发启动竞争
        time.sleep(0.05)
        self._stop_event = threading.Event()

    def start(self):
        with self.lock:
            FakeStation.started_count += 1
        self._stop_event.wait(timeout=2.0)
        return True

    def stop(self):
        self._stop_event.set()

    def get_status(self):
        return {"fake": True}


class RTKManagerConcurrencyTests(unittest.TestCase):
    def setUp(self):
        FakeStation.started_count = 0

    def test_concurrent_start_only_one_succeeds(self):
        manager = RTKManager()
        barrier = threading.Barrier(3)
        results = []
        result_lock = threading.Lock()

        def worker():
            barrier.wait()
            ok = manager.start_service()
            with result_lock:
                results.append(ok)

        with patch("app.web.services.rtk_manager.RTKBaseStation", FakeStation):
            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()

            # 同时释放两个并发启动请求
            barrier.wait()
            t1.join(timeout=2.0)
            t2.join(timeout=2.0)

            self.assertEqual(len(results), 2)
            self.assertEqual(sorted(results), [False, True])
            self.assertTrue(manager.is_running())
            self.assertEqual(FakeStation.started_count, 1)

            manager.stop_service()


if __name__ == "__main__":
    unittest.main()
