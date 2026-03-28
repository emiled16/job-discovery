from job_discovery_backend.worker.tasks import SYNC_ALL_COMPANIES_TASK_NAME


def load_schedule(interval_seconds: int) -> dict[str, dict[str, object]]:
    return {
        "global-sync": {
            "task": SYNC_ALL_COMPANIES_TASK_NAME,
            "schedule": interval_seconds,
        }
    }
