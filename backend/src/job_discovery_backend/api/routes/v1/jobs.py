from __future__ import annotations

from datetime import UTC, date, datetime, time
from math import ceil
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from job_discovery_backend.api.dependencies import get_current_user, get_db_session
from job_discovery_backend.api.errors import ApiError
from job_discovery_backend.api.jobs.filters import JobFilterParams, parse_job_filters
from job_discovery_backend.api.query import PaginationParams, SortParams, parse_pagination_params, parse_sort_params
from job_discovery_backend.api.validation import normalize_optional_text
from job_discovery_backend.db.models import Application, Company, Job, User
from job_discovery_backend.db.schema import APPLICATION_STATUSES

router = APIRouter(prefix="/jobs", tags=["jobs"])

JOB_SORT_FIELDS = {
    "company_name": Company.name,
    "created_at": Job.created_at,
    "posted_at": Job.posted_at,
    "title": Job.title,
}


class ApplicationUpsertPayload(BaseModel):
    status: str
    applied_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in APPLICATION_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(APPLICATION_STATUSES)}")
        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)


def _pagination_dependency(page: int = Query(1), per_page: int = Query(20)) -> PaginationParams:
    return parse_pagination_params(page=page, per_page=per_page)


def _sort_dependency(sort: str | None = Query(None), order: str | None = Query(None)) -> SortParams:
    return parse_sort_params(
        sort=sort,
        order=order,
        allowed_fields=set(JOB_SORT_FIELDS),
        default_field="posted_at",
    )


def _filter_dependency(
    title: str | None = Query(None),
    location: str | None = Query(None),
    company_ids: list[str] | None = Query(None),
    work_modes: list[str] | None = Query(None),
    posted_after: date | None = Query(None),
    posted_before: date | None = Query(None),
) -> JobFilterParams:
    return parse_job_filters(
        title=title,
        location=location,
        company_ids=company_ids,
        work_modes=work_modes,
        posted_after=posted_after,
        posted_before=posted_before,
    )


def _apply_job_filters(statement: Select, filters: JobFilterParams) -> Select:
    if filters.title:
        statement = statement.where(Job.title.ilike(f"%{filters.title}%"))
    if filters.location:
        statement = statement.where(Job.location_text.ilike(f"%{filters.location}%"))
    if filters.company_ids:
        statement = statement.where(Job.company_id.in_(filters.company_ids))
    if filters.work_modes:
        statement = statement.where(Job.work_mode.in_(filters.work_modes))
    if filters.posted_after:
        statement = statement.where(Job.posted_at >= _start_of_day(filters.posted_after))
    if filters.posted_before:
        statement = statement.where(Job.posted_at <= _end_of_day(filters.posted_before))
    return statement


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def _order_clauses(sort_params: SortParams) -> list:
    column = JOB_SORT_FIELDS[sort_params.field]
    direction = column.asc() if sort_params.direction == "asc" else column.desc()
    if sort_params.field in {"posted_at", "created_at"}:
        return [column.is_(None), direction, Job.id.asc()]
    return [direction, Job.id.asc()]


def _serialize_application(application: Application | None) -> dict | None:
    if application is None:
        return None
    return {
        "id": application.id,
        "status": application.status,
        "applied_at": application.applied_at,
        "notes": application.notes,
    }


def _serialize_job_list_item(job: Job, company: Company, application: Application | None) -> dict:
    preview = (job.description_text or "")[:200]
    return {
        "id": job.id,
        "title": job.title,
        "company": {
            "id": company.id,
            "slug": company.slug,
            "name": company.name,
        },
        "location_text": job.location_text,
        "work_mode": job.work_mode,
        "employment_type": job.employment_type,
        "status": job.status,
        "posted_at": job.posted_at,
        "apply_url": job.apply_url,
        "description_preview": preview,
        "application": _serialize_application(application),
    }


def _serialize_job_detail(job: Job, company: Company, application: Application | None) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": {
            "id": company.id,
            "slug": company.slug,
            "name": company.name,
            "website_url": company.website_url,
            "description": company.description,
            "lifecycle_status": company.lifecycle_status,
        },
        "location_text": job.location_text,
        "work_mode": job.work_mode,
        "employment_type": job.employment_type,
        "status": job.status,
        "posted_at": job.posted_at,
        "closed_at": job.closed_at,
        "apply_url": job.apply_url,
        "description_text": job.description_text,
        "application": _serialize_application(application),
    }


@router.get("")
def list_jobs(
    pagination: PaginationParams = Depends(_pagination_dependency),
    sort: SortParams = Depends(_sort_dependency),
    filters: JobFilterParams = Depends(_filter_dependency),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    base_statement = select(Job).join(Company).where(Job.status == "active")
    base_statement = _apply_job_filters(base_statement, filters)
    total = session.scalar(select(func.count()).select_from(base_statement.subquery())) or 0

    statement = (
        select(Job, Company, Application)
        .join(Company, Company.id == Job.company_id)
        .outerjoin(Application, (Application.job_id == Job.id) & (Application.user_id == current_user.id))
        .where(Job.status == "active")
    )
    statement = _apply_job_filters(statement, filters)
    rows = session.execute(
        statement.order_by(*_order_clauses(sort)).offset(pagination.offset).limit(pagination.per_page)
    ).all()

    return {
        "data": [_serialize_job_list_item(job, company, application) for job, company, application in rows],
        "meta": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": total,
            "total_pages": ceil(total / pagination.per_page) if total else 0,
        },
    }


@router.get("/{job_id}")
def get_job_detail(
    job_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    statement = (
        select(Job, Company, Application)
        .join(Company, Company.id == Job.company_id)
        .outerjoin(Application, (Application.job_id == Job.id) & (Application.user_id == current_user.id))
        .where(Job.id == job_id)
    )
    row = session.execute(statement).one_or_none()
    if row is None:
        raise ApiError(404, "job_not_found", "Job not found")

    job, company, application = row
    return {"data": _serialize_job_detail(job, company, application)}


@router.put("/{job_id}/application")
def upsert_application(
    job_id: str,
    payload: ApplicationUpsertPayload,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    job = session.get(Job, job_id)
    if job is None:
        raise ApiError(404, "job_not_found", "Job not found")

    application = session.scalar(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.job_id == job.id,
        )
    )

    applied_at = payload.applied_at
    if payload.status == "saved":
        applied_at = None
    elif applied_at is None:
        applied_at = application.applied_at if application and application.applied_at else datetime.now(UTC)

    if application is None:
        application = Application(
            id=str(uuid4()),
            user_id=current_user.id,
            job_id=job.id,
            status=payload.status,
            applied_at=applied_at,
            notes=payload.notes,
        )
        session.add(application)
    else:
        application.status = payload.status
        application.applied_at = applied_at
        application.notes = payload.notes

    session.commit()
    company = session.get(Company, job.company_id)
    return {
        "data": {
            "id": application.id,
            "status": application.status,
            "applied_at": application.applied_at,
            "notes": application.notes,
            "job": {
                "id": job.id,
                "title": job.title,
                "status": job.status,
            },
            "company": {
                "id": company.id,
                "slug": company.slug,
                "name": company.name,
            },
            "created_at": application.created_at,
            "updated_at": application.updated_at,
        }
    }
