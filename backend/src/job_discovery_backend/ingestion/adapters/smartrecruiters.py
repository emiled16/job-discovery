from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from job_discovery_backend.db.models import CompanySource
from job_discovery_backend.ingestion.adapters.base import BaseJobSourceAdapter, fetch_json
from job_discovery_backend.ingestion.models import AdapterFetchResult, IngestionError, NormalizedJob

_EXTERNAL_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PAGE_SIZE = 100


def _external_key(source: CompanySource) -> str:
    candidate = (source.external_key or "").strip()
    if not candidate:
        raise IngestionError("smartrecruiters sources require external_key")
    if not _EXTERNAL_KEY_PATTERN.fullmatch(candidate):
        raise IngestionError("smartrecruiters external_key contains unsupported characters")
    return candidate


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(UTC)


def _work_mode(location: dict[str, Any]) -> str:
    if location.get("hybrid") is True:
        return "hybrid"
    if location.get("remote") is True:
        return "remote"
    return "onsite"


def _detail_description(detail: dict[str, Any]) -> str | None:
    job_ad = detail.get("jobAd")
    if not isinstance(job_ad, dict):
        return None
    sections = job_ad.get("sections")
    if not isinstance(sections, dict):
        return None
    parts: list[str] = []
    for section in sections.values():
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip()
        text = str(section.get("text") or "").strip()
        if title and text:
            parts.append(f"{title}\n{text}")
        elif text:
            parts.append(text)
    return "\n\n".join(parts) or None


class SmartRecruitersAdapter(BaseJobSourceAdapter):
    def __init__(self, *, timeout_seconds: int = 30) -> None:
        super().__init__(source_type="smartrecruiters", request_timeout_seconds=timeout_seconds)

    def build_request_url(self, source: CompanySource) -> str:
        return f"https://api.smartrecruiters.com/v1/companies/{_external_key(source)}/postings"

    def parse_payload(self, payload: object, source: CompanySource) -> AdapterFetchResult:
        if not isinstance(payload, dict):
            raise IngestionError("smartrecruiters payload must be an object")
        postings = payload.get("content")
        if not isinstance(postings, list):
            raise IngestionError("smartrecruiters payload must include a content list")

        normalized_jobs: list[NormalizedJob] = []
        for posting in postings:
            if not isinstance(posting, dict):
                raise IngestionError("smartrecruiters postings must be objects")
            location = posting.get("location")
            if not isinstance(location, dict):
                location = {}
            employment = posting.get("typeOfEmployment")
            employment_type = None
            if isinstance(employment, dict):
                employment_type = str(employment.get("label") or "").strip() or None
            normalized_jobs.append(
                NormalizedJob(
                    source_job_key=str(posting.get("id") or ""),
                    title=str(posting.get("name") or ""),
                    location_text=str(location.get("fullLocation") or "").strip() or None,
                    work_mode=_work_mode(location),
                    employment_type=employment_type,
                    posted_at=_parse_datetime(str(posting.get("releasedDate") or "").strip() or None),
                    source_updated_at=None,
                    apply_url=None,
                    description_text=None,
                    raw_payload=posting,
                )
            )
        return AdapterFetchResult(jobs=tuple(normalized_jobs))

    def fetch(self, source: CompanySource) -> AdapterFetchResult:
        company_key = _external_key(source)
        postings: list[dict[str, Any]] = []
        offset = 0
        total_found: int | None = None

        while total_found is None or offset < total_found:
            payload = fetch_json(
                f"{self.build_request_url(source)}?limit={_PAGE_SIZE}&offset={offset}",
                timeout_seconds=self.request_timeout_seconds,
            )
            if not isinstance(payload, dict):
                raise IngestionError("smartrecruiters payload must be an object")
            content = payload.get("content")
            total_value = payload.get("totalFound")
            if not isinstance(content, list) or not isinstance(total_value, int):
                raise IngestionError("smartrecruiters payload must include content and totalFound")
            postings.extend(posting for posting in content if isinstance(posting, dict))
            total_found = total_value
            if not content:
                break
            offset += len(content)

        jobs: list[NormalizedJob] = []
        for posting in postings:
            detail_url = f"https://api.smartrecruiters.com/v1/companies/{company_key}/postings/{posting['id']}"
            detail: dict[str, Any] | None = None
            try:
                payload = fetch_json(detail_url, timeout_seconds=self.request_timeout_seconds)
                if isinstance(payload, dict):
                    detail = payload
            except IngestionError:
                detail = None

            location = posting.get("location")
            if not isinstance(location, dict):
                location = {}
            employment = posting.get("typeOfEmployment")
            employment_type = None
            if isinstance(employment, dict):
                employment_type = str(employment.get("label") or "").strip() or None
            jobs.append(
                NormalizedJob(
                    source_job_key=str(posting.get("id") or ""),
                    title=str(posting.get("name") or ""),
                    location_text=str(location.get("fullLocation") or "").strip() or None,
                    work_mode=_work_mode(location),
                    employment_type=employment_type,
                    posted_at=_parse_datetime(str(posting.get("releasedDate") or "").strip() or None),
                    source_updated_at=None,
                    apply_url=None if detail is None else str(detail.get("applyUrl") or "").strip() or None,
                    description_text=None if detail is None else _detail_description(detail),
                    raw_payload={**posting, "detail": detail},
                )
            )

        return AdapterFetchResult(jobs=tuple(jobs))
