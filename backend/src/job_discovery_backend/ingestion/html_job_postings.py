from __future__ import annotations

from datetime import UTC, datetime
from html import unescape
import json
import re
from typing import Any

from job_discovery_backend.ingestion.models import IngestionError, NormalizedJob, infer_work_mode

_JSON_LD_PATTERN = re.compile(
    r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    flags=re.IGNORECASE | re.DOTALL,
)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def iter_job_postings(value: object) -> list[dict[str, Any]]:
    postings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        value_type = value.get("@type")
        if value_type == "JobPosting" or (isinstance(value_type, list) and "JobPosting" in value_type):
            postings.append(value)
        for nested in value.values():
            postings.extend(iter_job_postings(nested))
    elif isinstance(value, list):
        for nested in value:
            postings.extend(iter_job_postings(nested))
    return postings


def extract_job_postings_from_html(html: str) -> list[dict[str, Any]]:
    postings: list[dict[str, Any]] = []
    for raw_json in _JSON_LD_PATTERN.findall(html):
        try:
            parsed = json.loads(unescape(raw_json.strip()))
        except ValueError:
            continue
        postings.extend(iter_job_postings(parsed))
    return postings


def _location_from_json_ld(job: dict[str, Any]) -> str | None:
    job_location = job.get("jobLocation")
    locations = job_location if isinstance(job_location, list) else [job_location]
    parts: list[str] = []
    for entry in locations:
        if not isinstance(entry, dict):
            continue
        address = entry.get("address")
        if not isinstance(address, dict):
            continue
        location_parts = [
            _string(address.get("addressLocality")),
            _string(address.get("addressRegion")),
            _string(address.get("addressCountry")),
        ]
        rendered = ", ".join(part for part in location_parts if part)
        if rendered:
            parts.append(rendered)
    if parts:
        return " / ".join(parts)
    return _string(job.get("jobLocationType"))


def normalize_json_ld_job(job: dict[str, Any], *, fallback_url: str) -> NormalizedJob:
    location_text = _location_from_json_ld(job)
    employment_type = _string(job.get("employmentType"))
    url = _string(job.get("url")) or fallback_url
    identifier = job.get("identifier")
    if isinstance(identifier, dict):
        source_job_key = _string(identifier.get("value")) or _string(identifier.get("name"))
    else:
        source_job_key = _string(identifier)
    job_location_type = _string(job.get("jobLocationType"))
    if job_location_type and "telecommute" in job_location_type.lower():
        work_mode = "remote"
    else:
        work_mode = infer_work_mode(location_text, employment_type, job_location_type)
    return NormalizedJob(
        source_job_key=source_job_key or url or _string(job.get("title")) or "",
        title=_string(job.get("title")) or "",
        location_text=location_text,
        work_mode=work_mode,
        employment_type=employment_type,
        posted_at=_parse_datetime(_string(job.get("datePosted"))),
        source_updated_at=_parse_datetime(_string(job.get("dateModified"))),
        apply_url=url,
        description_text=_string(job.get("description")),
        raw_payload=job,
    )


def extract_normalized_jobs_from_html(html: str, *, fallback_url: str) -> tuple[NormalizedJob, ...]:
    extracted_jobs: list[NormalizedJob] = []
    for job in extract_job_postings_from_html(html):
        try:
            extracted_jobs.append(normalize_json_ld_job(job, fallback_url=fallback_url))
        except IngestionError:
            continue
    return tuple(extracted_jobs)
