from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.worker.config import ConfigError, load_settings


class WorkerConfigTests(unittest.TestCase):
    def test_invalid_broker_url_raises_descriptive_error(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            "WORKER_BROKER_URL must be a valid URL",
        ):
            load_settings({"WORKER_BROKER_URL": "amqp://localhost"})

    def test_invalid_result_backend_raises_descriptive_error(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            "WORKER_RESULT_BACKEND must be a valid URL",
        ):
            load_settings({"WORKER_RESULT_BACKEND": "redis://"})


if __name__ == "__main__":
    unittest.main()

