def load_schedule(interval_seconds: int) -> dict[str, dict[str, object]]:
    return {
        "global-sync": {
            "task": "worker.ping",
            "schedule": interval_seconds,
        }
    }

