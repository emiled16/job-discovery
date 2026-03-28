from __future__ import annotations

from datetime import UTC, date, datetime, time
from math import ceil
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from job_discovery_backend.api.dependencies import get_current_user, get_db_session
from job_discovery_backend.api.errors import ApiError, get_request_id
from job_discovery_backend.api.query import PaginationParams, SortParams, parse_pagination_params, parse_sort_params
from job_discovery_backend.api.validation import normalize_optional_text, validate_http_url
from job_discovery_backend.db.models import Company, CompanySource, PipelineRun, PipelineRunEvent, User
from job_discovery_backend.db.schema import COMPANY_LIFECYCLE_STATES, COMPANY_SOURCE_TYPES, PIPELINE_RUN_STATUSES
from job_discovery_backend.worker.tasks import SYNC_COMPANY_TASK_NAME, dispatch_company_sync

router = APIRouter(prefix="/admin", tags=["admin"])

PIPELINE_RUN_SORT_FIELDS = {
    "finished_at": PipelineRun.finished_at,
    "started_at": PipelineRun.started_at,
    "status": PipelineRun.status,
}

ALLOWED_TRANSITIONS = {
    "draft": {"draft", "active", "paused", "archived"},
    "active": {"active", "paused", "archived"},
    "paused": {"paused", "active", "archived"},
    "archived": {"archived"},
}


class AdminCompanySourcePayload(BaseModel):
    source_type: str
    external_key: str | None = Field(default=None, max_length=255)
    base_url: str | None = Field(default=None, max_length=1024)
    configuration: dict = Field(default_factory=dict)
    is_enabled: bool = True

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str) -> str:
        if value not in COMPANY_SOURCE_TYPES:
            raise ValueError(f"source_type must be one of: {', '.join(COMPANY_SOURCE_TYPES)}")
        return value

    @field_validator("external_key", mode="before")
    @classmethod
    def normalize_external_key(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        return validate_http_url(value, field_name="base_url")


class AdminCompanyCreatePayload(BaseModel):
    slug: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    website_url: str | None = Field(default=None, max_length=1024)
    description: str | None = None
    lifecycle_status: str = "draft"
    source: AdminCompanySourcePayload

    @field_validator("slug", "name", mode="before")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = normalize_optional_text(value)
        if normalized is None:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("website_url", mode="before")
    @classmethod
    def validate_website_url(cls, value: str | None) -> str | None:
        return validate_http_url(value, field_name="website_url")

    @field_validator("lifecycle_status")
    @classmethod
    def validate_lifecycle_status(cls, value: str) -> str:
        if value not in COMPANY_LIFECYCLE_STATES:
            raise ValueError(f"lifecycle_status must be one of: {', '.join(COMPANY_LIFECYCLE_STATES)}")
        return value


class AdminCompanySourcePatchPayload(BaseModel):
    source_type: str | None = None
    external_key: str | None = Field(default=None, max_length=255)
    base_url: str | None = Field(default=None, max_length=1024)
    configuration: dict | None = None
    is_enabled: bool | None = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in COMPANY_SOURCE_TYPES:
            raise ValueError(f"source_type must be one of: {', '.join(COMPANY_SOURCE_TYPES)}")
        return value

    @field_validator("external_key", mode="before")
    @classmethod
    def normalize_external_key(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        return validate_http_url(value, field_name="base_url")


class AdminCompanyPatchPayload(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    website_url: str | None = Field(default=None, max_length=1024)
    description: str | None = None
    lifecycle_status: str | None = None
    source: AdminCompanySourcePatchPayload | None = None

    @field_validator("slug", "name", mode="before")
    @classmethod
    def normalize_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_optional_text(value)
        if normalized is None:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @field_validator("website_url", mode="before")
    @classmethod
    def validate_website_url(cls, value: str | None) -> str | None:
        return validate_http_url(value, field_name="website_url")

    @field_validator("lifecycle_status")
    @classmethod
    def validate_lifecycle_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in COMPANY_LIFECYCLE_STATES:
            raise ValueError(f"lifecycle_status must be one of: {', '.join(COMPANY_LIFECYCLE_STATES)}")
        return value

    @model_validator(mode="after")
    def require_change(self) -> "AdminCompanyPatchPayload":
        if (
            self.slug is None
            and self.name is None
            and self.website_url is None
            and self.description is None
            and self.lifecycle_status is None
            and self.source is None
        ):
            raise ValueError("At least one field must be provided")
        return self


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


def _serialize_source(source: CompanySource) -> dict:
    return {
        "id": source.id,
        "source_type": source.source_type,
        "external_key": source.external_key,
        "base_url": source.base_url,
        "configuration": source.configuration,
        "is_enabled": source.is_enabled,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }


def _serialize_company(company: Company, sources: list[CompanySource]) -> dict:
    return {
        "id": company.id,
        "slug": company.slug,
        "name": company.name,
        "website_url": company.website_url,
        "description": company.description,
        "lifecycle_status": company.lifecycle_status,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "sources": [_serialize_source(source) for source in sources],
    }


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


def _company_sources(session: Session, company_id: str) -> list[CompanySource]:
    return session.scalars(
        select(CompanySource).where(CompanySource.company_id == company_id).order_by(CompanySource.created_at.asc())
    ).all()


def _primary_source(session: Session, company_id: str) -> CompanySource | None:
    return session.scalar(
        select(CompanySource)
        .where(CompanySource.company_id == company_id)
        .order_by(CompanySource.created_at.asc(), CompanySource.id.asc())
        .limit(1)
    )


def _validate_transition(current_status: str, next_status: str) -> None:
    if next_status not in ALLOWED_TRANSITIONS[current_status]:
        raise ApiError(422, "invalid_state_transition", "Invalid company lifecycle transition")


@router.get("/companies")
def list_companies(session: Session = Depends(get_db_session)) -> dict:
    companies = session.scalars(select(Company).order_by(Company.name.asc())).all()
    return {"data": [_serialize_company(company, _company_sources(session, company.id)) for company in companies]}


@router.post("/companies", status_code=201)
def create_company(
    payload: AdminCompanyCreatePayload,
    session: Session = Depends(get_db_session),
) -> dict:
    company = Company(
        id=str(uuid4()),
        slug=payload.slug,
        name=payload.name,
        website_url=payload.website_url,
        description=payload.description,
        lifecycle_status=payload.lifecycle_status,
    )
    try:
        session.add(company)
        session.add(
            CompanySource(
                id=str(uuid4()),
                company_id=company.id,
                source_type=payload.source.source_type,
                external_key=payload.source.external_key,
                base_url=payload.source.base_url,
                configuration=payload.source.configuration,
                is_enabled=payload.source.is_enabled,
            )
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ApiError(409, "company_conflict", "Company already exists") from exc

    return {"data": _serialize_company(company, _company_sources(session, company.id))}


@router.patch("/companies/{company_id}")
def update_company(
    company_id: str,
    payload: AdminCompanyPatchPayload,
    session: Session = Depends(get_db_session),
) -> dict:
    company = session.get(Company, company_id)
    if company is None:
        raise ApiError(404, "company_not_found", "Company not found")

    if payload.lifecycle_status is not None:
        _validate_transition(company.lifecycle_status, payload.lifecycle_status)
        company.lifecycle_status = payload.lifecycle_status
    if payload.slug is not None:
        company.slug = payload.slug
    if payload.name is not None:
        company.name = payload.name
    if payload.website_url is not None:
        company.website_url = payload.website_url
    if payload.description is not None:
        company.description = payload.description

    if payload.source is not None:
        source = _primary_source(session, company.id)
        if source is None:
            if payload.source.source_type is None:
                raise ApiError(422, "source_type_required", "source.source_type is required when creating metadata")
            source = CompanySource(
                id=str(uuid4()),
                company_id=company.id,
                source_type=payload.source.source_type,
                external_key=payload.source.external_key,
                base_url=payload.source.base_url,
                configuration=payload.source.configuration or {},
                is_enabled=payload.source.is_enabled if payload.source.is_enabled is not None else True,
            )
            session.add(source)
        else:
            if payload.source.source_type is not None:
                source.source_type = payload.source.source_type
            if payload.source.external_key is not None:
                source.external_key = payload.source.external_key
            if payload.source.base_url is not None:
                source.base_url = payload.source.base_url
            if payload.source.configuration is not None:
                source.configuration = payload.source.configuration
            if payload.source.is_enabled is not None:
                source.is_enabled = payload.source.is_enabled

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ApiError(409, "company_conflict", "Company already exists") from exc

    return {"data": _serialize_company(company, _company_sources(session, company.id))}


@router.post("/companies/{company_id}/sync", status_code=202)
def trigger_company_sync(
    company_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    company = session.get(Company, company_id)
    if company is None:
        raise ApiError(404, "company_not_found", "Company not found")

    request_id = get_request_id(request)
    payload = {
        "company_id": company.id,
        "requested_by_user_id": current_user.id,
        "request_id": request_id,
    }
    dispatch_company_sync(payload)

    return {
        "data": {
            "task_name": SYNC_COMPANY_TASK_NAME,
            "company_id": company.id,
            "request_id": request_id,
            "status": "queued",
        }
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
