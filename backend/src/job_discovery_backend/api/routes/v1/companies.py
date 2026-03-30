from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from job_discovery_backend.api.dependencies import get_current_user, get_db_session
from job_discovery_backend.api.errors import ApiError, get_request_id
from job_discovery_backend.api.validation import normalize_optional_text, validate_http_url
from job_discovery_backend.db.models import Company, CompanySource, User
from job_discovery_backend.db.schema import COMPANY_LIFECYCLE_STATES, COMPANY_SOURCE_TYPES
from job_discovery_backend.ingestion.pipeline import create_sync_request
from job_discovery_backend.worker.tasks import SYNC_COMPANY_TASK_NAME, dispatch_company_sync

router = APIRouter(prefix="/companies", tags=["companies"])

ALLOWED_TRANSITIONS = {
    "draft": {"draft", "active", "paused", "archived"},
    "active": {"active", "paused", "archived"},
    "paused": {"paused", "active", "archived"},
    "archived": {"archived"},
}


class CompanySourcePayload(BaseModel):
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


class CompanyCreatePayload(BaseModel):
    slug: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    website_url: str | None = Field(default=None, max_length=1024)
    description: str | None = None
    lifecycle_status: str = "draft"
    source: CompanySourcePayload

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


class CompanySourcePatchPayload(BaseModel):
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


class CompanyPatchPayload(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    website_url: str | None = Field(default=None, max_length=1024)
    description: str | None = None
    lifecycle_status: str | None = None
    source: CompanySourcePatchPayload | None = None

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
    def require_change(self) -> "CompanyPatchPayload":
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


def _validate_transition(current_status: str, next_status: str) -> None:
    if next_status not in ALLOWED_TRANSITIONS[current_status]:
        raise ApiError(422, "invalid_state_transition", "Invalid company lifecycle transition")


@router.get("")
def list_companies(session: Session = Depends(get_db_session)) -> dict:
    companies = session.scalars(select(Company).order_by(Company.name.asc())).all()
    return {"data": [_serialize_company(company, _company_sources(session, company.id)) for company in companies]}


@router.post("", status_code=201)
def create_company(
    payload: CompanyCreatePayload,
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


@router.patch("/{company_id}")
def update_company(
    company_id: str,
    payload: CompanyPatchPayload,
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


@router.post("/{company_id}/sync", status_code=202)
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
    sync_request = create_sync_request(
        session,
        company_id=company.id,
        requested_by_user_id=current_user.id,
        request_id=request_id,
        trigger_type="manual",
    )
    session.commit()
    dispatch_company_sync(sync_request.as_payload())

    return {
        "data": {
            "task_name": SYNC_COMPANY_TASK_NAME,
            "company_id": company.id,
            "pipeline_run_id": sync_request.pipeline_run_id,
            "request_id": request_id,
            "status": "queued",
        }
    }
