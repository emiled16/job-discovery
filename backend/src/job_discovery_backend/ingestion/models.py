from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
import re
from typing import Any

from job_discovery_backend.db.schema import JOB_WORK_MODES
from job_discovery_backend.urls import validate_public_http_url_optional

_BREAK_TAG_PATTERN = re.compile(r"(?i)<br\s*/?>")
_BLOCK_CLOSE_PATTERN = re.compile(r"(?i)</(?:p|div|section|article|ul|ol|li|h[1-6]|tr|table)>")
_LIST_OPEN_PATTERN = re.compile(r"(?i)<li[^>]*>")
_TAG_PATTERN = re.compile(r"<[^>]+>")
_INLINE_SPACE_PATTERN = re.compile(r"[^\S\n]+")
_BLANK_LINE_PATTERN = re.compile(r"\n{3,}")
_HTML_ENTITY_ESCAPE_GUARD = 3


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
    try:
        return validate_public_http_url_optional(value, field_name=field_name)
    except ValueError as exc:
        raise IngestionError(str(exc)) from exc


def _normalize_datetime(value: datetime | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise IngestionError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _decode_html_entities(value: str) -> str:
    decoded = value
    for _ in range(_HTML_ENTITY_ESCAPE_GUARD):
        next_value = unescape(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return decoded


def _normalize_description_text(value: str | None) -> str | None:
    normalized = _normalize_text(value, field_name="description_text")
    if normalized is None:
        return None

    normalized = _decode_html_entities(normalized).replace("\xa0", " ")
    normalized = _BREAK_TAG_PATTERN.sub("\n", normalized)
    normalized = _BLOCK_CLOSE_PATTERN.sub("\n", normalized)
    normalized = _LIST_OPEN_PATTERN.sub("- ", normalized)
    normalized = _TAG_PATTERN.sub(" ", normalized)
    normalized = _INLINE_SPACE_PATTERN.sub(" ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = _BLANK_LINE_PATTERN.sub("\n\n", normalized)
    normalized = normalized.strip()
    return normalized or None


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
        description_text = _normalize_description_text(self.description_text)
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
