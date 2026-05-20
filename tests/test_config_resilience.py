import tempfile
import unittest
from pathlib import Path

from app.core.config import Config


class ConfigResilienceTest(unittest.TestCase):
    def _write_config(self, content: str) -> str:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        config_path = Path(tmp_dir.name) / "config.yaml"
        config_path.write_text(content, encoding="utf-8")
        return str(config_path)

    def test_invalid_reconnect_keeps_other_sections(self):
        config_path = self._write_config(
            """
serial:
  port: /dev/ttyS1
  baudrate: 115200
ntrip:
  host: caster.example.com
  port: 2101
  mountpoint: MP
  username: user
  password: pass
reconnect:
  max_retries: 0
  retry_delay: 2.5
base_station:
  latitude: 30.0
  longitude: 120.0
  altitude: 12.0
  enable_arp_average: 0
"""
        )

        cfg = Config(config_path)

        self.assertEqual(cfg.get_serial_config().port, "/dev/ttyS1")
        self.assertEqual(cfg.get_ntrip_config().host, "caster.example.com")
        # 非法节回退默认值
        self.assertEqual(cfg.get_reconnect_config().max_retries, 5)

    def test_invalid_serial_section_type_only_resets_serial(self):
        config_path = self._write_config(
            """
serial: invalid
ntrip:
  host: caster.example.com
  port: 2101
"""
        )

        cfg = Config(config_path)

        # serial 节非法，回退默认
        self.assertEqual(cfg.get_serial_config().port, "/dev/ttyUSB0")
        # 其他节仍保留
        self.assertEqual(cfg.get_ntrip_config().host, "caster.example.com")


if __name__ == "__main__":
    unittest.main()
