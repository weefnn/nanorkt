import logging
import threading
import time
import unittest
from unittest.mock import patch

from app.drivers.serial_reader import SerialReader
from app.web.services.rtk_manager import RTKManager
import app.web.services.rtk_manager as rtk_manager_module

_REAL_THREAD = threading.Thread


class _FakeStation:
    def __init__(self):
        self.stop_called = False

    def start(self):
        return True

    def stop(self):
        self.stop_called = True

    def get_status(self):
        return {}


class _FakeThread:
    def __init__(self, target=None, args=(), name=None, daemon=None):
        self._alive = False
        self._target = target
        self._args = args

    def start(self):
        # 放大并发窗口，让两个 start 请求尽可能重叠
        time.sleep(0.05)
        self._alive = True

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        self._alive = False


class _AlwaysAliveThread:
    def __init__(self):
        self.join_called = False

    def is_alive(self):
        return True

    def join(self, timeout=None):
        self.join_called = True


class _BlockingSerial:
    def __init__(self, first_read_started: threading.Event, release_read: threading.Event):
        self.is_open = True
        self._first_read_started = first_read_started
        self._release_read = release_read
        self._in_waiting_calls = 0

    @property
    def in_waiting(self):
        self._in_waiting_calls += 1
        if self._in_waiting_calls == 1:
            self._first_read_started.set()
            self._release_read.wait(timeout=1.0)
            return 1
        return 0

    def read(self, size):
        return b"x" * size

    def close(self):
        self.is_open = False


class _ErrorCaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            self.records.append(record)


class CriticalRaceFixTests(unittest.TestCase):
    def test_start_service_is_serialized_under_concurrency(self):
        manager = RTKManager()
        results = []
        start_barrier = threading.Barrier(2)

        def _call_start():
            start_barrier.wait()
            results.append(manager.start_service())

        with patch.object(rtk_manager_module, "RTKBaseStation", _FakeStation), patch.object(
            rtk_manager_module.threading, "Thread", _FakeThread
        ):
            t1 = _REAL_THREAD(target=_call_start)
            t2 = _REAL_THREAD(target=_call_start)
            t1.start()
            t2.start()
            t1.join(timeout=2.0)
            t2.join(timeout=2.0)

        self.assertEqual(len(results), 2, "两个并发请求都应返回结果")
        self.assertEqual(results.count(True), 1, "并发启动只能成功一次")
        self.assertEqual(results.count(False), 1, "并发启动应拒绝重复请求")

    def test_stop_service_keeps_running_state_when_thread_still_alive(self):
        manager = RTKManager()
        station = _FakeStation()
        thread = _AlwaysAliveThread()
        manager.station = station
        manager.thread = thread
        manager._running = True

        stopped = manager.stop_service()

        self.assertFalse(stopped, "线程未退出时 stop 应返回失败")
        self.assertTrue(manager.is_running(), "线程仍存活时不能标记为已停止")
        self.assertIs(manager.thread, thread)
        self.assertIs(manager.station, station)
        self.assertTrue(station.stop_called, "stop 仍需向站点发送停止请求")
        self.assertTrue(thread.join_called, "stop 应等待线程退出")

    def test_stop_during_read_does_not_log_spurious_error(self):
        reader = SerialReader("/dev/ttyUSB0", 115200)
        first_read_started = threading.Event()
        release_read = threading.Event()
        reader.serial = _BlockingSerial(first_read_started, release_read)

        log_handler = _ErrorCaptureHandler()
        logger = logging.getLogger("app.drivers.serial_reader")
        logger.addHandler(log_handler)
        previous_level = logger.level
        logger.setLevel(logging.DEBUG)
        self.addCleanup(logger.removeHandler, log_handler)
        self.addCleanup(logger.setLevel, previous_level)

        worker = threading.Thread(target=reader.read_data, args=(lambda _: None,))
        worker.start()
        self.assertTrue(first_read_started.wait(timeout=1.0), "读取循环未按预期启动")

        reader.stop()
        release_read.set()
        worker.join(timeout=2.0)

        self.assertFalse(worker.is_alive(), "停止后读取线程应退出")
        self.assertFalse(reader.is_running, "停止后 is_running 应为 False")
        self.assertEqual(log_handler.records, [], "停止流程不应产生 ERROR 级别异常日志")


if __name__ == "__main__":
    unittest.main()
