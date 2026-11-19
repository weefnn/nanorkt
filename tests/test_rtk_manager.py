import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
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

    def __init__(self, target, name=None, daemon=None):
        self._target = target
        self._alive = False

    def start(self):
        self._alive = True
        try:
            self._target()
        finally:
            self._alive = False

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        return None


class FailingThread:
    """模拟线程启动失败。"""

    def __init__(self, target, name=None, daemon=None):
        self._target = target

    def start(self):
        raise RuntimeError("thread start failed")

    def is_alive(self):
        return False

    def join(self, timeout=None):
        return None


class RTKManagerTestCase(unittest.TestCase):
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
