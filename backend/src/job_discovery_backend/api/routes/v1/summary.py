from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from job_discovery_backend.api.dependencies import get_current_user, get_db_session
from job_discovery_backend.api.errors import ApiError
from job_discovery_backend.db.models import Application, Job, SavedView, User

router = APIRouter(prefix="/summary", tags=["summary"])


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def _timeseries_filters(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    bucket: str = Query("day"),
) -> tuple[date | None, date | None, str]:
    if bucket not in {"day", "week"}:
        raise ApiError(
            422,
            "invalid_query",
            "Invalid summary filters",
            details=[{"field": "bucket", "message": "Must be one of: day, week", "code": "invalid_choice"}],
        )
    if start_date and end_date and start_date > end_date:
        raise ApiError(
            422,
            "invalid_query",
            "Invalid summary filters",
            details=[{"field": "start_date", "message": "Must be on or before end_date", "code": "invalid_range"}],
        )
    return start_date, end_date, bucket


def _bucket_start(value: datetime, bucket: str) -> date:
    bucket_date = value.date()
    if bucket == "week":
        return bucket_date - timedelta(days=bucket_date.weekday())
    return bucket_date


def _bucket_sequence(start_date: date, end_date: date, bucket: str) -> list[date]:
    step = timedelta(days=7 if bucket == "week" else 1)
    values: list[date] = []
    current = start_date
    while current <= end_date:
        values.append(current)
        current += step
    return values


@router.get("/metrics")
def get_summary_metrics(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    total_jobs = session.scalar(select(func.count()).select_from(Job).where(Job.status == "active")) or 0
    applied_jobs = session.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.user_id == current_user.id, Application.status != "saved")
    ) or 0
    saved_view_count = session.scalar(
        select(func.count()).select_from(SavedView).where(SavedView.user_id == current_user.id)
    ) or 0

    return {
        "data": {
            "total_jobs": total_jobs,
            "applied_jobs": applied_jobs,
            "saved_views": saved_view_count,
            "application_rate": (applied_jobs / total_jobs) if total_jobs else 0,
        }
    }


@router.get("/timeseries")
def get_summary_timeseries(
    filters: tuple[date | None, date | None, str] = Depends(_timeseries_filters),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    start_date, end_date, bucket = filters

    statement = select(Application.applied_at).where(
        Application.user_id == current_user.id,
        Application.status != "saved",
        Application.applied_at.is_not(None),
    )
    if start_date:
        statement = statement.where(Application.applied_at >= _start_of_day(start_date))
    if end_date:
        statement = statement.where(Application.applied_at <= _end_of_day(end_date))

    applied_timestamps = [value for value in session.scalars(statement) if value is not None]
    if bucket == "week":
        if start_date is not None:
            start_date = start_date - timedelta(days=start_date.weekday())
        if end_date is not None:
            end_date = end_date - timedelta(days=end_date.weekday())

    if not applied_timestamps:
        if start_date is None or end_date is None:
            return {"data": []}
        sequence = _bucket_sequence(start_date, end_date, bucket)
        return {"data": [{"bucket_start": value.isoformat(), "count": 0} for value in sequence]}

    counts = Counter(_bucket_start(value, bucket) for value in applied_timestamps)
    effective_start = start_date or min(counts)
    effective_end = end_date or max(counts)
    if bucket == "week":
        effective_start = effective_start - timedelta(days=effective_start.weekday())
        effective_end = effective_end - timedelta(days=effective_end.weekday())

    sequence = _bucket_sequence(effective_start, effective_end, bucket)
    return {"data": [{"bucket_start": value.isoformat(), "count": counts.get(value, 0)} for value in sequence]}
