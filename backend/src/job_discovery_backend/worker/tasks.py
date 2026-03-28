from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from job_discovery_backend.ingestion.processor import build_company_sync_processor
from job_discovery_backend.ingestion.pipeline import SyncCompanyRequest, process_sync_request, run_scheduled_sync
from job_discovery_backend.worker.celery_app import celery_app
from job_discovery_backend.worker.config import load_settings

SYNC_ALL_COMPANIES_TASK_NAME = "pipeline.sync_all_companies"
SYNC_COMPANY_TASK_NAME = "pipeline.sync_company"


def dispatch_company_sync(payload: Mapping[str, Any]) -> Any:
    return celery_app.send_task(SYNC_COMPANY_TASK_NAME, kwargs=dict(payload))


@celery_app.task(name=SYNC_COMPANY_TASK_NAME)
def sync_company_task(**payload: Any) -> dict[str, Any]:
    settings = load_settings()
    request = SyncCompanyRequest(
        pipeline_run_id=str(payload["pipeline_run_id"]),
        company_id=str(payload["company_id"]),
        requested_by_user_id=None
        if payload.get("requested_by_user_id") is None
        else str(payload["requested_by_user_id"]),
        request_id=None if payload.get("request_id") is None else str(payload["request_id"]),
        trigger_type=str(payload.get("trigger_type") or "manual"),
    )
    outcome = process_sync_request(
        settings.database_url,
        request,
        processor=build_company_sync_processor(
            missed_cycle_threshold=settings.job_closure_missed_cycles,
        ),
    )
    return {"pipeline_run_id": request.pipeline_run_id, "status": outcome.status, "details": outcome.details}


@celery_app.task(name=SYNC_ALL_COMPANIES_TASK_NAME)
def sync_all_companies_task() -> dict[str, Any]:
    settings = load_settings()
    return run_scheduled_sync(
        settings.database_url,
        max_workers=settings.max_company_sync_workers,
        processor=build_company_sync_processor(
            missed_cycle_threshold=settings.job_closure_missed_cycles,
        ),
    )
