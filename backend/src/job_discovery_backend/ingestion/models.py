from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from job_discovery_backend.db.schema import JOB_WORK_MODES


class IngestionError(ValueError):
    """Raised when source payloads cannot be normalized safely."""


def _normalize_text(value: str | None, *, field_name: str, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise IngestionError(f"{field_name} is required")
        return None

    normalized = value.strip()
    if not normalized:
        if required:
            raise IngestionError(f"{field_name} is required")
        return None
    return normalized


def _normalize_url(value: str | None, *, field_name: str) -> str | None:
    normalized = _normalize_text(value, field_name=field_name)
    if normalized is None:
        return None

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise IngestionError(f"{field_name} must be an absolute http(s) URL")
    return normalized


def _normalize_datetime(value: datetime | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise IngestionError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def infer_work_mode(*values: str | None) -> str:
    haystack = " ".join(value.lower() for value in values if value).strip()
    if not haystack:
        return "unknown"
    if "hybrid" in haystack:
        return "hybrid"
    if "remote" in haystack or "distributed" in haystack:
        return "remote"
    if "onsite" in haystack or "on-site" in haystack or "office" in haystack:
        return "onsite"
    return "unknown"


@dataclass(frozen=True)
class NormalizedJob:
    source_job_key: str
    title: str
    location_text: str | None
    work_mode: str
    employment_type: str | None
    posted_at: datetime | None
    source_updated_at: datetime | None
    apply_url: str | None
    description_text: str | None
    raw_payload: dict[str, Any]

    def __post_init__(self) -> None:
        source_job_key = _normalize_text(self.source_job_key, field_name="source_job_key", required=True)
        title = _normalize_text(self.title, field_name="title", required=True)
        location_text = _normalize_text(self.location_text, field_name="location_text")
        employment_type = _normalize_text(self.employment_type, field_name="employment_type")
        apply_url = _normalize_url(self.apply_url, field_name="apply_url")
        description_text = _normalize_text(self.description_text, field_name="description_text")
        posted_at = _normalize_datetime(self.posted_at, field_name="posted_at")
        source_updated_at = _normalize_datetime(self.source_updated_at, field_name="source_updated_at")

        if self.work_mode not in JOB_WORK_MODES:
            raise IngestionError(f"work_mode must be one of: {', '.join(JOB_WORK_MODES)}")
        if not isinstance(self.raw_payload, dict):
            raise IngestionError("raw_payload must be a mapping object")

        object.__setattr__(self, "source_job_key", source_job_key)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "location_text", location_text)
        object.__setattr__(self, "employment_type", employment_type)
        object.__setattr__(self, "apply_url", apply_url)
        object.__setattr__(self, "description_text", description_text)
        object.__setattr__(self, "posted_at", posted_at)
        object.__setattr__(self, "source_updated_at", source_updated_at)

    def normalized_payload(self) -> dict[str, Any]:
        return {
            "source_job_key": self.source_job_key,
            "title": self.title,
            "location_text": self.location_text,
            "work_mode": self.work_mode,
            "employment_type": self.employment_type,
            "posted_at": None if self.posted_at is None else self.posted_at.isoformat(),
            "source_updated_at": None if self.source_updated_at is None else self.source_updated_at.isoformat(),
            "apply_url": self.apply_url,
            "description_text": self.description_text,
        }


@dataclass(frozen=True)
class AdapterFetchResult:
    jobs: tuple[NormalizedJob, ...]
