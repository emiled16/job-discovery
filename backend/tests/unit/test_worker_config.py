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

    def test_invalid_max_company_sync_workers_raises_descriptive_error(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            "WORKER_MAX_COMPANY_SYNC_WORKERS must be a positive integer",
        ):
            load_settings({"WORKER_MAX_COMPANY_SYNC_WORKERS": "0"})

    def test_invalid_job_closure_threshold_raises_descriptive_error(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            "WORKER_JOB_CLOSURE_MISSED_CYCLES must be a positive integer",
        ):
            load_settings({"WORKER_JOB_CLOSURE_MISSED_CYCLES": "0"})


if __name__ == "__main__":
    unittest.main()
