from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.scheduler.schedule import load_schedule  # noqa: E402
from job_discovery_backend.worker.tasks import SYNC_ALL_COMPANIES_TASK_NAME  # noqa: E402


def test_scheduler_registers_global_sync_task() -> None:
    schedule = load_schedule(900)

    assert schedule == {
        "global-sync": {
            "task": SYNC_ALL_COMPANIES_TASK_NAME,
            "schedule": 900,
        }
    }
