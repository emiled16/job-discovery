from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


def validate_public_http_url(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be a valid http or https URL")
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} must not include credentials")
    if parsed.fragment:
        raise ValueError(f"{field_name} must not include a fragment")

    hostname = parsed.hostname
    if hostname is None:
        raise ValueError(f"{field_name} must include a hostname")
    if _is_forbidden_host(hostname):
        raise ValueError(f"{field_name} must target a public hostname")

    return normalized


def validate_public_http_url_optional(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return validate_public_http_url(normalized, field_name=field_name)


def _is_forbidden_host(hostname: str) -> bool:
    normalized = hostname.strip().lower()
    if not normalized:
        return True
    if normalized in {"localhost", "localhost.localdomain"}:
        return True
    if normalized.endswith(".local"):
        return True

    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return "." not in normalized

    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )
