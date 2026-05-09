import threading
import time
import unittest
import types
import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch

# 避免测试依赖 FastAPI 等运行时环境：直接加载目标模块并注入假依赖
_fake_station_module = types.ModuleType("app.core.station")
_fake_station_module.RTKBaseStation = object
sys.modules["app.core.station"] = _fake_station_module

_module_path = Path(__file__).resolve().parents[1] / "app" / "web" / "services" / "rtk_manager.py"
_module_spec = importlib.util.spec_from_file_location("rtk_manager_under_test", _module_path)
rtk_manager = importlib.util.module_from_spec(_module_spec)
assert _module_spec and _module_spec.loader
_module_spec.loader.exec_module(rtk_manager)


class BlockingFakeStation:
    """用于模拟停止超时场景的假基站。"""

    def __init__(self):
        self.started_event = threading.Event()
        self.stop_called = threading.Event()
        self.finish_event = threading.Event()

    def start(self) -> bool:
        self.started_event.set()
        self.stop_called.wait(timeout=2.0)
        self.finish_event.wait(timeout=2.0)
        return True

    def stop(self) -> None:
        self.stop_called.set()

    def get_status(self) -> dict:
        return {"fake_station": True}


class RTKManagerConcurrencyTest(unittest.TestCase):
    @patch.object(rtk_manager, "RTKBaseStation", BlockingFakeStation)
    def test_stop_timeout_does_not_allow_second_start(self):
        manager = rtk_manager.RTKManager()
        manager.STOP_TIMEOUT = 0.05

        self.assertTrue(manager.start_service())
        station = manager.station
        self.assertIsNotNone(station)
        self.assertTrue(station.started_event.wait(timeout=1.0))

        # 线程未真正退出时，停止应返回失败，并保持运行中状态
        self.assertFalse(manager.stop_service())
        self.assertTrue(manager.is_running())

        # 停止未完成期间不允许再次启动，避免并发双实例
        self.assertFalse(manager.start_service())

        # 放行线程退出，状态应最终恢复为未运行
        station.finish_event.set()
        deadline = time.time() + 1.0
        while manager.is_running() and time.time() < deadline:
            time.sleep(0.01)
        self.assertFalse(manager.is_running())


if __name__ == "__main__":
    unittest.main()
