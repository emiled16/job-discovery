from __future__ import annotations

from datetime import UTC, date, datetime, time
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from job_discovery_backend.api.dependencies import get_db_session
from job_discovery_backend.api.errors import ApiError
from job_discovery_backend.api.query import PaginationParams, SortParams, parse_pagination_params, parse_sort_params
from job_discovery_backend.db.models import Company, PipelineRun, PipelineRunEvent
from job_discovery_backend.db.schema import PIPELINE_RUN_STATUSES

router = APIRouter(prefix="/admin", tags=["admin"])

PIPELINE_RUN_SORT_FIELDS = {
    "finished_at": PipelineRun.finished_at,
    "started_at": PipelineRun.started_at,
    "status": PipelineRun.status,
}


def _pagination_dependency(page: int = Query(1), per_page: int = Query(20)) -> PaginationParams:
    return parse_pagination_params(page=page, per_page=per_page)


def _run_sort_dependency(sort: str | None = Query(None), order: str | None = Query(None)) -> SortParams:
    return parse_sort_params(
        sort=sort,
        order=order,
        allowed_fields=set(PIPELINE_RUN_SORT_FIELDS),
        default_field="started_at",
    )


def _run_filter_dependency(
    company_id: str | None = Query(None),
    statuses: list[str] | None = Query(None),
    started_after: date | None = Query(None),
    started_before: date | None = Query(None),
) -> tuple[str | None, tuple[str, ...], date | None, date | None]:
    normalized_statuses = tuple(status.strip() for status in statuses or [] if status.strip())
    invalid_statuses = sorted(set(normalized_statuses).difference(PIPELINE_RUN_STATUSES))
    if invalid_statuses:
        raise ApiError(
            422,
            "invalid_query",
            "Invalid pipeline run filters",
            details=[
                {
                    "field": "statuses",
                    "message": f"Must be drawn from: {', '.join(PIPELINE_RUN_STATUSES)}",
                    "code": "invalid_choice",
                }
            ],
        )
    if started_after and started_before and started_after > started_before:
        raise ApiError(
            422,
            "invalid_query",
            "Invalid pipeline run filters",
            details=[
                {
                    "field": "started_after",
                    "message": "Must be on or before started_before",
                    "code": "invalid_range",
                }
            ],
        )
    return company_id, normalized_statuses, started_after, started_before


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def _order_clauses(sort_params: SortParams) -> list:
    column = PIPELINE_RUN_SORT_FIELDS[sort_params.field]
    direction = column.asc() if sort_params.direction == "asc" else column.desc()
    return [column.is_(None), direction, PipelineRun.id.asc()]


def _serialize_pipeline_run(run: PipelineRun, company: Company | None) -> dict:
    return {
        "id": run.id,
        "company": None if company is None else {"id": company.id, "slug": company.slug, "name": company.name},
        "requested_by_user_id": run.requested_by_user_id,
        "trigger_type": run.trigger_type,
        "status": run.status,
        "request_id": run.request_id,
        "details": run.details,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


def _serialize_pipeline_event(event: PipelineRunEvent) -> dict:
    return {
        "id": event.id,
        "company_id": event.company_id,
        "event_type": event.event_type,
        "level": event.level,
        "sequence_number": event.sequence_number,
        "message": event.message,
        "payload": event.payload,
        "created_at": event.created_at,
    }


@router.get("/pipeline-runs")
def list_pipeline_runs(
    pagination: PaginationParams = Depends(_pagination_dependency),
    sort: SortParams = Depends(_run_sort_dependency),
    filters: tuple[str | None, tuple[str, ...], date | None, date | None] = Depends(_run_filter_dependency),
    session: Session = Depends(get_db_session),
) -> dict:
    company_id, statuses, started_after, started_before = filters

    statement = select(PipelineRun, Company).outerjoin(Company, Company.id == PipelineRun.company_id)
    count_statement = select(func.count()).select_from(PipelineRun)

    if company_id:
        statement = statement.where(PipelineRun.company_id == company_id)
        count_statement = count_statement.where(PipelineRun.company_id == company_id)
    if statuses:
        statement = statement.where(PipelineRun.status.in_(statuses))
        count_statement = count_statement.where(PipelineRun.status.in_(statuses))
    if started_after:
        statement = statement.where(PipelineRun.started_at >= _start_of_day(started_after))
        count_statement = count_statement.where(PipelineRun.started_at >= _start_of_day(started_after))
    if started_before:
        statement = statement.where(PipelineRun.started_at <= _end_of_day(started_before))
        count_statement = count_statement.where(PipelineRun.started_at <= _end_of_day(started_before))

    total = session.scalar(count_statement) or 0
    rows = session.execute(
        statement.order_by(*_order_clauses(sort)).offset(pagination.offset).limit(pagination.per_page)
    ).all()

    return {
        "data": [_serialize_pipeline_run(run, company) for run, company in rows],
        "meta": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": total,
            "total_pages": ceil(total / pagination.per_page) if total else 0,
        },
    }


@router.get("/pipeline-runs/{run_id}")
def get_pipeline_run_detail(
    run_id: str,
    session: Session = Depends(get_db_session),
) -> dict:
    row = session.execute(
        select(PipelineRun, Company).outerjoin(Company, Company.id == PipelineRun.company_id).where(PipelineRun.id == run_id)
    ).one_or_none()
    if row is None:
        raise ApiError(404, "pipeline_run_not_found", "Pipeline run not found")

    run, company = row
    events = session.scalars(
        select(PipelineRunEvent)
        .where(PipelineRunEvent.pipeline_run_id == run.id)
        .order_by(PipelineRunEvent.sequence_number.asc(), PipelineRunEvent.created_at.asc())
    ).all()

    return {
        "data": {
            **_serialize_pipeline_run(run, company),
            "events": [_serialize_pipeline_event(event) for event in events],
        }
    }
