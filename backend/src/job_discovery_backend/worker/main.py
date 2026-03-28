from celery.bin.worker import worker as celery_worker

from job_discovery_backend.worker.celery_app import celery_app


def main() -> None:
    worker = celery_worker(app=celery_app)
    worker.run(
        loglevel="INFO",
        pool="solo",
        without_heartbeat=False,
        without_gossip=True,
        without_mingle=True,
    )


if __name__ == "__main__":
    main()

