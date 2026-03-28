from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from job_discovery_backend.worker.celery_app import celery_app

SYNC_COMPANY_TASK_NAME = "pipeline.sync_company"


def dispatch_company_sync(payload: Mapping[str, Any]) -> Any:
    return celery_app.send_task(SYNC_COMPANY_TASK_NAME, kwargs=dict(payload))
