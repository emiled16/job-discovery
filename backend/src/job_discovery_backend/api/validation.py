from __future__ import annotations

from urllib.parse import urlparse


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def validate_http_url(value: str | None, *, field_name: str) -> str | None:
    normalized = normalize_optional_text(value)
    if normalized is None:
        return None

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be a valid http or https URL")
    return normalized
