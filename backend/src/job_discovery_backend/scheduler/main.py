from job_discovery_backend.observability import configure_logging
from job_discovery_backend.scheduler.celery_app import celery_app


def main() -> None:
    configure_logging("scheduler")
    celery_app.start(
        [
            "beat",
            "--loglevel=INFO",
            "--schedule=/tmp/celerybeat-schedule",
        ]
    )


if __name__ == "__main__":
    main()
