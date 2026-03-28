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
