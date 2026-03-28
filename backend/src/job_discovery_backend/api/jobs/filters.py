from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from job_discovery_backend.api.errors import ApiError
from job_discovery_backend.db.schema import JOB_WORK_MODES


@dataclass(frozen=True)
class JobFilterParams:
    title: str | None
    location: str | None
    company_ids: tuple[str, ...]
    work_modes: tuple[str, ...]
    posted_after: date | None
    posted_before: date | None


def parse_job_filters(
    *,
    title: str | None = None,
    location: str | None = None,
    company_ids: list[str] | None = None,
    work_modes: list[str] | None = None,
    posted_after: date | None = None,
    posted_before: date | None = None,
) -> JobFilterParams:
    normalized_title = title.strip() if title else None
    normalized_location = location.strip() if location else None
    normalized_company_ids = tuple(company_id.strip() for company_id in company_ids or [] if company_id.strip())
    normalized_work_modes = tuple(mode.strip().lower() for mode in work_modes or [] if mode.strip())

    errors: list[dict[str, str]] = []
    invalid_modes = sorted(set(normalized_work_modes).difference(JOB_WORK_MODES))
    if invalid_modes:
        errors.append(
            {
                "field": "work_modes",
                "message": f"Must be drawn from: {', '.join(JOB_WORK_MODES)}",
                "code": "invalid_choice",
            }
        )

    if posted_after and posted_before and posted_after > posted_before:
        errors.append(
            {
                "field": "posted_after",
                "message": "Must be on or before posted_before",
                "code": "invalid_range",
            }
        )

    if errors:
        raise ApiError(
            422,
            "invalid_query",
            "Invalid job filters",
            details=errors,
        )

    return JobFilterParams(
        title=normalized_title or None,
        location=normalized_location or None,
        company_ids=normalized_company_ids,
        work_modes=normalized_work_modes,
        posted_after=posted_after,
        posted_before=posted_before,
    )
