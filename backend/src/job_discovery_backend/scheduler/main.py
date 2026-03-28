from celery.bin.beat import beat as celery_beat

from job_discovery_backend.scheduler.celery_app import celery_app


def main() -> None:
    beat = celery_beat(app=celery_app)
    beat.run(
        loglevel="INFO",
    )


if __name__ == "__main__":
    main()

