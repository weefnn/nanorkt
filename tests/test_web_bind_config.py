import os
import unittest

from app.web.server_config import get_server_bind_config


class WebBindConfigTests(unittest.TestCase):
    def test_defaults_to_loopback_and_default_port(self):
        old_host = os.environ.pop("NANORTK_WEB_HOST", None)
        old_port = os.environ.pop("NANORTK_WEB_PORT", None)
        try:
            host, port = get_server_bind_config()
            self.assertEqual(host, "127.0.0.1")
            self.assertEqual(port, 8000)
        finally:
            if old_host is not None:
                os.environ["NANORTK_WEB_HOST"] = old_host
            if old_port is not None:
                os.environ["NANORTK_WEB_PORT"] = old_port

    def test_reads_env_override(self):
        old_host = os.environ.get("NANORTK_WEB_HOST")
        old_port = os.environ.get("NANORTK_WEB_PORT")
        try:
            os.environ["NANORTK_WEB_HOST"] = "0.0.0.0"
            os.environ["NANORTK_WEB_PORT"] = "9000"
            host, port = get_server_bind_config()
            self.assertEqual(host, "0.0.0.0")
            self.assertEqual(port, 9000)
        finally:
            if old_host is None:
                os.environ.pop("NANORTK_WEB_HOST", None)
            else:
                os.environ["NANORTK_WEB_HOST"] = old_host

            if old_port is None:
                os.environ.pop("NANORTK_WEB_PORT", None)
            else:
                os.environ["NANORTK_WEB_PORT"] = old_port


if __name__ == "__main__":
    unittest.main()
