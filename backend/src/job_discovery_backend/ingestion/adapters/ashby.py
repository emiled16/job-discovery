from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any
from urllib.parse import urlparse

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.adapters.base import BaseJobSourceAdapter
from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError, NormalizedJob, infer_work_mode

_EXTERNAL_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_WORK_MODE_MAP = {
    "onsite": "onsite",
    "remote": "remote",
    "hybrid": "hybrid",
}


def _external_key(source: CompanySource) -> str:
    candidate: str | None = None
    if source.external_key and source.external_key.strip():
        candidate = source.external_key.strip()
    elif source.base_url:
        path = urlparse(source.base_url).path.strip("/")
        if path:
            candidate = path.split("/")[0]

    if candidate is None:
        raise IngestionError("ashby sources require external_key or base_url")
    if not _EXTERNAL_KEY_PATTERN.fullmatch(candidate):
        raise IngestionError("ashby external_key contains unsupported characters")
    return candidate


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(UTC)


def _location_text(job: dict[str, Any]) -> str | None:
    location = job.get("location")
    if isinstance(location, str) and location.strip():
        return location.strip()

    address = job.get("address")
    if not isinstance(address, dict):
        return None
    postal_address = address.get("postalAddress")
    if not isinstance(postal_address, dict):
        return None

    parts = [
        str(postal_address.get("addressLocality") or "").strip(),
        str(postal_address.get("addressRegion") or "").strip(),
        str(postal_address.get("addressCountry") or "").strip(),
    ]
    normalized_parts = [part for part in parts if part]
    return ", ".join(normalized_parts) or None


def _work_mode(job: dict[str, Any], location_text: str | None, employment_type: str | None) -> str:
    workplace_type = str(job.get("workplaceType") or "").strip().lower()
    if workplace_type in _WORK_MODE_MAP:
        return _WORK_MODE_MAP[workplace_type]
    if job.get("isRemote") is True:
        return "remote"
    return infer_work_mode(location_text, employment_type)


class AshbyAdapter(BaseJobSourceAdapter):
    def __init__(self, *, timeout_seconds: int = 30) -> None:
        super().__init__(source_type="ashby", request_timeout_seconds=timeout_seconds)

    def build_request_url(self, source: CompanySource) -> str:
        return f"https://api.ashbyhq.com/posting-api/job-board/{_external_key(source)}"

    def parse_payload(self, payload: object, source: CompanySource) -> AdapterFetchResult:
        if not isinstance(payload, dict):
            raise IngestionError("ashby payload must be an object")
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise IngestionError("ashby payload must include a jobs list")

        normalized_jobs: list[NormalizedJob] = []
        for job in jobs:
            if not isinstance(job, dict):
                raise IngestionError("ashby jobs must be objects")
            if job.get("isListed") is False:
                continue

            employment_type = None if job.get("employmentType") is None else str(job.get("employmentType"))
            location_text = _location_text(job)
            normalized_jobs.append(
                NormalizedJob(
                    source_job_key=str(job.get("id") or job.get("jobUrl") or ""),
                    title=str(job.get("title") or ""),
                    location_text=location_text,
                    work_mode=_work_mode(job, location_text, employment_type),
                    employment_type=employment_type,
                    posted_at=_parse_datetime(str(job.get("publishedAt") or "").strip() or None),
                    source_updated_at=None,
                    apply_url=None if job.get("applyUrl") is None else str(job.get("applyUrl")),
                    description_text=None
                    if job.get("descriptionPlain") is None and job.get("descriptionHtml") is None
                    else str(job.get("descriptionPlain") or job.get("descriptionHtml")),
                    raw_payload=job,
                )
            )

        return AdapterFetchResult(jobs=tuple(normalized_jobs))
