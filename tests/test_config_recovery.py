import tempfile
import unittest
from pathlib import Path

from app.core.config import Config


class ConfigRecoveryTest(unittest.TestCase):
    def test_recover_from_malformed_yaml_via_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            config_path.write_text(
                "serial:\n  port: /dev/ttyUSB0\n  baudrate: [115200\n",
                encoding="utf-8",
            )

            config = Config(str(config_path))
            self.assertIsNotNone(config.app_config)

            saved = config.save({"serial": {"port": "/dev/ttyS0", "baudrate": 115200}})
            self.assertTrue(saved)

            reloaded = Config(str(config_path))
            serial_cfg = reloaded.get_serial_config()
            self.assertEqual(serial_cfg.port, "/dev/ttyS0")
            self.assertEqual(serial_cfg.baudrate, 115200)


if __name__ == "__main__":
    unittest.main()
