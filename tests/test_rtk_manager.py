import threading
import time
import unittest
from unittest.mock import patch

from app.web.services.rtk_manager import RTKManager


class _FakeStation:
    instances = []

    def __init__(self):
        self._stop_event = threading.Event()
        _FakeStation.instances.append(self)

    def start(self):
        self._stop_event.wait(timeout=2.0)

    def stop(self):
        self._stop_event.set()

    def get_status(self):
        return {"fake_station": True}


class RTKManagerConcurrencyTests(unittest.TestCase):
    def setUp(self):
        _FakeStation.instances = []
        self.manager = RTKManager()

    def tearDown(self):
        # 避免测试失败时遗留后台线程
        if self.manager.is_running():
            self.manager.stop_service()

    def test_concurrent_start_only_one_succeeds(self):
        """
        并发启动时只能有一个请求成功，避免创建孤儿线程。
        """
        start_gate = threading.Barrier(3)
        results = []
        errors = []

        def start_once():
            try:
                start_gate.wait(timeout=2.0)
                results.append(self.manager.start_service())
            except Exception as exc:  # pragma: no cover - 调试保护
                errors.append(exc)

        with patch("app.web.services.rtk_manager.RTKBaseStation", _FakeStation):
            t1 = threading.Thread(target=start_once)
            t2 = threading.Thread(target=start_once)
            t1.start()
            t2.start()

            # 同步释放两个启动线程
            start_gate.wait(timeout=2.0)

            t1.join(timeout=2.0)
            t2.join(timeout=2.0)

            self.assertFalse(errors, f"线程异常: {errors}")
            self.assertEqual(sum(results), 1, f"并发启动结果异常: {results}")
            self.assertEqual(len(_FakeStation.instances), 1)

            self.assertTrue(self.manager.is_running())
            self.assertTrue(self.manager.stop_service())
            self.assertFalse(self.manager.is_running())

    def test_start_stop_lifecycle(self):
        with patch("app.web.services.rtk_manager.RTKBaseStation", _FakeStation):
            self.assertTrue(self.manager.start_service())
            self.assertTrue(self.manager.is_running())

            # 给后台线程一点时间进入运行态
            time.sleep(0.05)
            status = self.manager.get_status()
            self.assertTrue(status["running"])

            self.assertTrue(self.manager.stop_service())
            self.assertFalse(self.manager.is_running())


if __name__ == "__main__":
    unittest.main()
