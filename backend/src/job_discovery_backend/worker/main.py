from job_discovery_backend.observability import configure_logging
from job_discovery_backend.worker.celery_app import celery_app


def main() -> None:
    configure_logging("worker")
    celery_app.worker_main(
        [
            "worker",
            "--loglevel=INFO",
            "--pool=solo",
            "--without-gossip",
            "--without-mingle",
        ]
    )


if __name__ == "__main__":
    main()
