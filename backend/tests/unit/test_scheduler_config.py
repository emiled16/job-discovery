from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.scheduler.config import ConfigError, load_settings


class SchedulerConfigTests(unittest.TestCase):
    def test_invalid_interval_raises_descriptive_error(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            "SCHEDULER_SYNC_INTERVAL_SECONDS must be a positive integer",
        ):
            load_settings({"SCHEDULER_SYNC_INTERVAL_SECONDS": "0"})

    def test_blank_timezone_raises_descriptive_error(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            "SCHEDULER_TIMEZONE must not be empty",
        ):
            load_settings({"SCHEDULER_TIMEZONE": " "})


if __name__ == "__main__":
    unittest.main()

