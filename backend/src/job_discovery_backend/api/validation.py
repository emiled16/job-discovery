from __future__ import annotations

from job_discovery_backend.urls import validate_public_http_url_optional


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def validate_http_url(value: str | None, *, field_name: str) -> str | None:
    return validate_public_http_url_optional(value, field_name=field_name)
