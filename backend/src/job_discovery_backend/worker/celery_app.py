from celery import Celery

from job_discovery_backend.worker.config import load_settings

settings = load_settings()

celery_app = Celery(
    "job_discovery_worker",
    broker=settings.broker_url,
    backend=settings.result_backend,
)

celery_app.conf.update(
    task_default_queue="job_discovery",
    task_ignore_result=False,
)


@celery_app.task(name="worker.ping")
def ping() -> str:
    return "pong"

