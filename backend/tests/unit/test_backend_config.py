from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.config import ConfigError, load_settings


class BackendConfigTests(unittest.TestCase):
    def test_invalid_port_raises_descriptive_error(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            "BACKEND_PORT must be an integer between 1 and 65535",
        ):
            load_settings({"BACKEND_PORT": "invalid"})

    def test_invalid_database_url_raises_descriptive_error(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            "DATABASE_URL must be a valid URL",
        ):
            load_settings({"DATABASE_URL": "sqlite:///tmp.db"})


if __name__ == "__main__":
    unittest.main()

