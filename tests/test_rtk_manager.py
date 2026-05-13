import importlib.util
import sys
import threading
import time
import types
import unittest
from pathlib import Path


def _load_rtk_manager_module():
    # 注入最小依赖，避免测试环境缺少完整运行依赖（如 pydantic/fastapi）导致导入失败。
    fake_station_module = types.ModuleType("app.core.station")

    class DummyStation:
        def start(self):
            pass

        def stop(self):
            pass

        def get_status(self):
            return {}

    fake_station_module.RTKBaseStation = DummyStation
    sys.modules["app.core.station"] = fake_station_module

    module_path = Path(__file__).resolve().parents[1] / "app/web/services/rtk_manager.py"
    spec = importlib.util.spec_from_file_location("rtk_manager_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


rtk_manager = _load_rtk_manager_module()


class BlockingStation:
    release_event = threading.Event()

    def __init__(self):
        self.stopped = False

    def start(self):
        self.release_event.wait(timeout=2.0)

    def stop(self):
        self.stopped = True

    def get_status(self):
        return {"fake_station": True}


class RTKManagerConcurrencyTest(unittest.TestCase):
    def setUp(self):
        self.original_station_class = rtk_manager.RTKBaseStation
        rtk_manager.RTKBaseStation = BlockingStation
        BlockingStation.release_event = threading.Event()
        rtk_manager.reset_manager()

    def tearDown(self):
        BlockingStation.release_event.set()
        manager = rtk_manager.get_manager()
        if manager.thread and manager.thread.is_alive():
            manager.thread.join(timeout=1.0)
        rtk_manager.reset_manager()
        rtk_manager.RTKBaseStation = self.original_station_class

    def test_stop_timeout_keeps_manager_running_and_blocks_restart(self):
        manager = rtk_manager.get_manager()
        manager.STOP_TIMEOUT = 0.01

        self.assertTrue(manager.start_service())
        self.assertTrue(manager.is_running())

        # 模拟 stop 超时：线程仍阻塞，stop 返回失败。
        self.assertFalse(manager.stop_service())
        self.assertTrue(manager.is_running())

        # 超时后必须阻止重复启动，避免并发服务实例互相覆盖状态。
        self.assertFalse(manager.start_service())

        # 放行工作线程，确认其退出后状态会自动恢复为未运行。
        BlockingStation.release_event.set()
        for _ in range(50):
            if not manager.is_running():
                break
            time.sleep(0.02)

        self.assertFalse(manager.is_running())


if __name__ == "__main__":
    unittest.main()
