from __future__ import annotations

from datetime import UTC, date, datetime, time
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from job_discovery_backend.api.dependencies import get_current_user, get_db_session
from job_discovery_backend.api.errors import ApiError
from job_discovery_backend.api.query import PaginationParams, SortParams, parse_pagination_params, parse_sort_params
from job_discovery_backend.db.models import Application, Company, Job, User
from job_discovery_backend.db.schema import APPLICATION_STATUSES

router = APIRouter(tags=["applications"])

APPLICATION_SORT_FIELDS = {
    "applied_at": Application.applied_at,
    "company_name": Company.name,
    "posted_at": Job.posted_at,
    "status": Application.status,
    "updated_at": Application.updated_at,
}


def _pagination_dependency(page: int = Query(1), per_page: int = Query(20)) -> PaginationParams:
    return parse_pagination_params(page=page, per_page=per_page)


def _sort_dependency(sort: str | None = Query(None), order: str | None = Query(None)) -> SortParams:
    return parse_sort_params(
        sort=sort,
        order=order,
        allowed_fields=set(APPLICATION_SORT_FIELDS),
        default_field="applied_at",
    )


def _application_filter_dependency(
    statuses: list[str] | None = Query(None),
    applied_after: date | None = Query(None),
    applied_before: date | None = Query(None),
) -> tuple[tuple[str, ...], date | None, date | None]:
    normalized_statuses = tuple(status.strip() for status in statuses or [] if status.strip())
    invalid_statuses = sorted(set(normalized_statuses).difference(APPLICATION_STATUSES))
    if invalid_statuses:
        raise ApiError(
            422,
            "invalid_query",
            "Invalid application filters",
            details=[
                {
                    "field": "statuses",
                    "message": f"Must be drawn from: {', '.join(APPLICATION_STATUSES)}",
                    "code": "invalid_choice",
                }
            ],
        )

    if applied_after and applied_before and applied_after > applied_before:
        raise ApiError(
            422,
            "invalid_query",
            "Invalid application filters",
            details=[
                {
                    "field": "applied_after",
                    "message": "Must be on or before applied_before",
                    "code": "invalid_range",
                }
            ],
        )

    return normalized_statuses, applied_after, applied_before


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def _order_clauses(sort_params: SortParams) -> list:
    column = APPLICATION_SORT_FIELDS[sort_params.field]
    direction = column.asc() if sort_params.direction == "asc" else column.desc()
    if sort_params.field in {"applied_at", "posted_at", "updated_at"}:
        return [column.is_(None), direction, Application.id.asc()]
    return [direction, Application.id.asc()]


def _serialize_application_record(application: Application, job: Job, company: Company) -> dict:
    return {
        "id": application.id,
        "status": application.status,
        "applied_at": application.applied_at,
        "notes": application.notes,
        "job": {
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "posted_at": job.posted_at,
            "location_text": job.location_text,
            "work_mode": job.work_mode,
            "apply_url": job.apply_url,
        },
        "company": {
            "id": company.id,
            "slug": company.slug,
            "name": company.name,
        },
        "created_at": application.created_at,
        "updated_at": application.updated_at,
    }


@router.get("/applications")
def list_applications(
    pagination: PaginationParams = Depends(_pagination_dependency),
    sort: SortParams = Depends(_sort_dependency),
    filters: tuple[tuple[str, ...], date | None, date | None] = Depends(_application_filter_dependency),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    statuses, applied_after, applied_before = filters

    statement = (
        select(Application, Job, Company)
        .join(Job, Job.id == Application.job_id)
        .join(Company, Company.id == Job.company_id)
        .where(Application.user_id == current_user.id)
    )
    count_statement = select(func.count()).select_from(Application).where(Application.user_id == current_user.id)

    if statuses:
        statement = statement.where(Application.status.in_(statuses))
        count_statement = count_statement.where(Application.status.in_(statuses))
    if applied_after:
        statement = statement.where(Application.applied_at >= _start_of_day(applied_after))
        count_statement = count_statement.where(Application.applied_at >= _start_of_day(applied_after))
    if applied_before:
        statement = statement.where(Application.applied_at <= _end_of_day(applied_before))
        count_statement = count_statement.where(Application.applied_at <= _end_of_day(applied_before))

    total = session.scalar(count_statement) or 0
    rows = session.execute(
        statement.order_by(*_order_clauses(sort)).offset(pagination.offset).limit(pagination.per_page)
    ).all()

    return {
        "data": [_serialize_application_record(application, job, company) for application, job, company in rows],
        "meta": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": total,
            "total_pages": ceil(total / pagination.per_page) if total else 0,
        },
    }
