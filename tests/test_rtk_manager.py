import importlib.util
import sys
import threading
import time
import types
import unittest
from pathlib import Path


def load_rtk_manager_module():
    """按文件路径加载模块，避免触发 web 包的额外依赖。"""
    # 注入最小化依赖，避免导入 app.core.__init__（其依赖 pydantic）
    app_module = types.ModuleType("app")
    core_module = types.ModuleType("app.core")
    station_module = types.ModuleType("app.core.station")

    class DummyRTKBaseStation:
        def start(self):
            return None

        def stop(self):
            return None

        def get_status(self):
            return {}

    station_module.RTKBaseStation = DummyRTKBaseStation
    core_module.station = station_module
    app_module.core = core_module

    sys.modules.setdefault("app", app_module)
    sys.modules["app.core"] = core_module
    sys.modules["app.core.station"] = station_module

    module_path = Path(__file__).resolve().parents[1] / "app" / "web" / "services" / "rtk_manager.py"
    spec = importlib.util.spec_from_file_location("rtk_manager_under_test", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 rtk_manager 模块")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BlockingStation:
    """模拟无法在短时间内退出的基站线程。"""

    instances = []
    started_event = threading.Event()
    release_event = threading.Event()

    def __init__(self):
        self.stop_called = False
        self.__class__.instances.append(self)

    def start(self):
        self.__class__.started_event.set()
        # 模拟线程长时间阻塞，确保 manager.stop_service 会超时
        self.__class__.release_event.wait(timeout=2.0)

    def stop(self):
        self.stop_called = True

    def get_status(self):
        return {"mock_station": True}


class RTKManagerStopTimeoutTest(unittest.TestCase):
    def setUp(self):
        self.rtk_manager = load_rtk_manager_module()
        self.rtk_manager.RTKBaseStation = BlockingStation
        self.manager = self.rtk_manager.get_manager()
        self.manager.STOP_TIMEOUT = 0.05

        BlockingStation.instances.clear()
        BlockingStation.started_event.clear()
        BlockingStation.release_event.clear()

    def tearDown(self):
        BlockingStation.release_event.set()
        thread = self.manager.thread
        if thread and thread.is_alive():
            thread.join(timeout=1.0)
        self.rtk_manager.reset_manager()

    def test_stop_timeout_keeps_running_state_and_blocks_second_start(self):
        self.assertTrue(self.manager.start_service())
        self.assertTrue(BlockingStation.started_event.wait(timeout=1.0))

        # 线程未退出时，stop 应失败且保持 running=True
        self.assertFalse(self.manager.stop_service())
        self.assertTrue(self.manager.is_running())

        # 仍在运行状态时，不允许再次启动第二个实例
        self.assertFalse(self.manager.start_service())
        self.assertEqual(len(BlockingStation.instances), 1)

        # 释放阻塞后线程退出，状态应回落为 stopped
        BlockingStation.release_event.set()
        thread = self.manager.thread
        if thread:
            thread.join(timeout=1.0)

        for _ in range(20):
            if not self.manager.is_running():
                break
            time.sleep(0.01)

        self.assertFalse(self.manager.is_running())


if __name__ == "__main__":
    unittest.main()
