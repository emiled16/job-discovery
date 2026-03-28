from __future__ import annotations

from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from job_discovery_backend.api.dependencies import get_current_user, get_db_session
from job_discovery_backend.api.errors import ApiError
from job_discovery_backend.api.jobs.filters import parse_job_filters
from job_discovery_backend.api.query import parse_sort_params
from job_discovery_backend.api.validation import normalize_optional_text
from job_discovery_backend.db.models import SavedView, User

router = APIRouter(prefix="/views", tags=["views"])

VIEW_SORT_FIELDS = {"company_name", "created_at", "posted_at", "title"}


class SavedViewFiltersPayload(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    company_ids: list[str] = Field(default_factory=list)
    work_modes: list[str] = Field(default_factory=list)
    posted_after: date | None = None
    posted_before: date | None = None

    @field_validator("title", "location", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def validate_supported_filters(self) -> "SavedViewFiltersPayload":
        try:
            parse_job_filters(
                title=self.title,
                location=self.location,
                company_ids=self.company_ids,
                work_modes=self.work_modes,
                posted_after=self.posted_after,
                posted_before=self.posted_before,
            )
        except ApiError as exc:
            raise ValueError(exc.message) from exc
        return self


class SavedViewSortPayload(BaseModel):
    field: str
    direction: str

    @model_validator(mode="after")
    def validate_sort(self) -> "SavedViewSortPayload":
        try:
            parse_sort_params(
                sort=self.field,
                order=self.direction,
                allowed_fields=VIEW_SORT_FIELDS,
                default_field="posted_at",
            )
        except ApiError as exc:
            raise ValueError(exc.message) from exc
        return self


class SavedViewCreatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    filters: SavedViewFiltersPayload
    sort: SavedViewSortPayload
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = normalize_optional_text(value)
        if normalized is None:
            raise ValueError("name must not be empty")
        return normalized


class SavedViewUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    filters: SavedViewFiltersPayload | None = None
    sort: SavedViewSortPayload | None = None
    is_default: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_optional_text(value)
        if normalized is None:
            raise ValueError("name must not be empty")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "SavedViewUpdatePayload":
        if self.name is None and self.filters is None and self.sort is None and self.is_default is None:
            raise ValueError("At least one field must be provided")
        return self


def _serialize_view(view: SavedView) -> dict:
    return {
        "id": view.id,
        "name": view.name,
        "filters": view.filters,
        "sort": view.sort,
        "is_default": view.is_default,
        "created_at": view.created_at,
        "updated_at": view.updated_at,
    }


def _filters_to_record(filters: SavedViewFiltersPayload) -> dict:
    record = filters.model_dump()
    for key in ("posted_after", "posted_before"):
        if record[key] is not None:
            record[key] = record[key].isoformat()
    return record


def _clear_other_defaults(session: Session, user_id: str, view_id: str | None = None) -> None:
    statement = select(SavedView).where(SavedView.user_id == user_id, SavedView.is_default.is_(True))
    if view_id is not None:
        statement = statement.where(SavedView.id != view_id)

    for view in session.scalars(statement):
        view.is_default = False


def _get_owned_view(session: Session, view_id: str, user_id: str) -> SavedView | None:
    return session.scalar(select(SavedView).where(SavedView.id == view_id, SavedView.user_id == user_id))


@router.post("", status_code=201)
def create_view(
    payload: SavedViewCreatePayload,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    view = SavedView(
        id=str(uuid4()),
        user_id=current_user.id,
        name=payload.name,
        filters=_filters_to_record(payload.filters),
        sort=payload.sort.model_dump(),
        is_default=payload.is_default,
    )
    session.add(view)
    if payload.is_default:
        _clear_other_defaults(session, current_user.id)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ApiError(409, "view_name_conflict", "Saved view name already exists") from exc

    return {"data": _serialize_view(view)}


@router.get("")
def list_views(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    views = session.scalars(
        select(SavedView)
        .where(SavedView.user_id == current_user.id)
        .order_by(SavedView.is_default.desc(), SavedView.name.asc())
    ).all()
    return {"data": [_serialize_view(view) for view in views]}


@router.get("/{view_id}")
def get_view(
    view_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    view = _get_owned_view(session, view_id, current_user.id)
    if view is None:
        raise ApiError(404, "view_not_found", "Saved view not found")
    return {"data": _serialize_view(view)}


@router.patch("/{view_id}")
def update_view(
    view_id: str,
    payload: SavedViewUpdatePayload,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    view = _get_owned_view(session, view_id, current_user.id)
    if view is None:
        raise ApiError(404, "view_not_found", "Saved view not found")

    if payload.name is not None:
        view.name = payload.name
    if payload.filters is not None:
        view.filters = _filters_to_record(payload.filters)
    if payload.sort is not None:
        view.sort = payload.sort.model_dump()
    if payload.is_default is not None:
        view.is_default = payload.is_default
        if payload.is_default:
            _clear_other_defaults(session, current_user.id, view.id)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ApiError(409, "view_name_conflict", "Saved view name already exists") from exc

    return {"data": _serialize_view(view)}


@router.delete("/{view_id}", status_code=204)
def delete_view(
    view_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    view = _get_owned_view(session, view_id, current_user.id)
    if view is not None:
        session.delete(view)
        session.commit()
    return Response(status_code=204)
