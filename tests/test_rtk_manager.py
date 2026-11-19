import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import threading
import time
import sys
import types
from unittest.mock import patch


def _load_rtk_manager_module():
    """按文件路径加载模块，避免依赖完整 Web 运行环境。"""
    station_module = types.ModuleType("app.core.station")
    station_module.RTKBaseStation = object
    sys.modules.setdefault("app.core.station", station_module)

    module_path = Path(__file__).resolve().parents[1] / "app/web/services/rtk_manager.py"
    spec = spec_from_file_location("rtk_manager_under_test", module_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


rtk_manager = _load_rtk_manager_module()
RTKManager = rtk_manager.RTKManager


class ImmediateThread:
    """同步执行 target，用于稳定复现启动竞态场景。"""

    def __init__(self, target, args=(), kwargs=None, name=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self._alive = False

    def start(self):
        self._alive = True
        try:
            self._target(*self._args, **self._kwargs)
        finally:
            self._alive = False

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        return None


class FailingThread:
    """模拟线程启动失败。"""

    def __init__(self, target, args=(), kwargs=None, name=None, daemon=None):
        self._target = target

    def start(self):
        raise RuntimeError("thread start failed")

    def is_alive(self):
        return False

    def join(self, timeout=None):
        return None


class RTKManagerTestCase(unittest.TestCase):
    def test_concurrent_start_should_only_allow_one_success(self):
        """并发 start 请求下只能有一个成功，防止双启动。"""
        manager = RTKManager()
        real_thread = threading.Thread
        result_lock = threading.Lock()
        results = []
        start_barrier = threading.Barrier(2)

        class NoopThread:
            def __init__(self, target, args=(), kwargs=None, name=None, daemon=None):
                self._alive = False

            def start(self):
                self._alive = True

            def is_alive(self):
                return self._alive

            def join(self, timeout=None):
                self._alive = False

        class FakeStation:
            def start(self):
                return True

            def stop(self):
                return None

        def slow_station_factory():
            time.sleep(0.05)
            return FakeStation()

        def runner():
            start_barrier.wait()
            result = manager.start_service()
            with result_lock:
                results.append(result)

        with patch.object(rtk_manager, "RTKBaseStation", side_effect=slow_station_factory):
            with patch.object(rtk_manager.threading, "Thread", NoopThread):
                t1 = real_thread(target=runner)
                t2 = real_thread(target=runner)
                t1.start()
                t2.start()
                t1.join()
                t2.join()

        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 1)

    def test_fast_failure_should_not_leave_manager_running(self):
        """服务快速失败后，管理器状态不应卡在 running=True。"""
        manager = RTKManager()

        with patch.object(rtk_manager, "RTKBaseStation") as station_cls:
            station_cls.return_value.start.return_value = False

            with patch.object(rtk_manager.threading, "Thread", ImmediateThread):
                first_result = manager.start_service()
                second_result = manager.start_service()

        self.assertTrue(first_result)
        self.assertTrue(second_result)
        self.assertFalse(manager.is_running())

    def test_thread_start_failure_should_rollback_state(self):
        """线程启动失败时应回滚 manager 内部状态。"""
        manager = RTKManager()

        with patch.object(rtk_manager, "RTKBaseStation"):
            with patch.object(rtk_manager.threading, "Thread", FailingThread):
                result = manager.start_service()

        self.assertFalse(result)
        self.assertFalse(manager.is_running())
        self.assertIsNone(manager.station)
        self.assertIsNone(manager.thread)


if __name__ == "__main__":
    unittest.main()
