import time
import unittest
from unittest.mock import patch

from app.web.services.rtk_manager import get_manager, reset_manager


class _FastExitStation:
    """立即退出的假基站，用于放大管理器状态竞争窗口。"""

    def start(self) -> bool:
        return False

    def stop(self) -> None:
        return None


class RTKManagerRaceTest(unittest.TestCase):
    def tearDown(self) -> None:
        reset_manager()

    def test_no_stale_running_flag_when_worker_exits_immediately(self) -> None:
        # 历史问题：线程先退出再由主线程把 _running 写回 True，导致状态卡死。
        with patch("app.web.services.rtk_manager.RTKBaseStation", _FastExitStation):
            for _ in range(200):
                reset_manager()
                manager = get_manager()

                started = manager.start_service()
                self.assertTrue(started)

                # 线程应很快退出；等待后状态必须一致为未运行。
                time.sleep(0.01)
                thread = manager.thread
                if thread and thread.is_alive():
                    thread.join(timeout=0.1)

                self.assertFalse(manager.is_running())
                self.assertFalse(manager.get_status()["thread_alive"])


if __name__ == "__main__":
    unittest.main()
