from celery import Celery

from job_discovery_backend.scheduler.config import load_settings
from job_discovery_backend.scheduler.schedule import load_schedule

settings = load_settings()

celery_app = Celery(
    "job_discovery_scheduler",
    broker=settings.broker_url,
    backend=settings.result_backend,
)

celery_app.conf.update(
    beat_schedule=load_schedule(settings.sync_interval_seconds),
    timezone=settings.timezone,
)

