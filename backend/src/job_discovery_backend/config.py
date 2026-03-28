from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid."""


@dataclass(frozen=True)
class BackendSettings:
    host: str
    port: int
    database_url: str
    redis_url: str


def _require_text(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key, default).strip()
    if not value:
        raise ConfigError(f"{key} must not be empty")
    return value


def _parse_port(env: Mapping[str, str], key: str, default: str) -> int:
    raw_value = env.get(key, default).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer between 1 and 65535") from exc

    if value < 1 or value > 65535:
        raise ConfigError(f"{key} must be an integer between 1 and 65535")

    return value


def _parse_url(
    env: Mapping[str, str],
    key: str,
    default: str,
    allowed_schemes: set[str],
) -> str:
    value = env.get(key, default).strip()
    parsed = urlparse(value)

    if parsed.scheme not in allowed_schemes or not parsed.netloc:
        allowed = ", ".join(sorted(allowed_schemes))
        raise ConfigError(f"{key} must be a valid URL with one of: {allowed}")

    return value


def load_settings(env: Mapping[str, str] | None = None) -> BackendSettings:
    source = env or {}

    return BackendSettings(
        host=_require_text(source, "BACKEND_HOST", "0.0.0.0"),
        port=_parse_port(source, "BACKEND_PORT", "8000"),
        database_url=_parse_url(
            source,
            "DATABASE_URL",
            "postgresql://job_discovery:job_discovery@postgres:5432/job_discovery",
            {"postgres", "postgresql"},
        ),
        redis_url=_parse_url(
            source,
            "REDIS_URL",
            "redis://redis:6379/0",
            {"redis", "rediss"},
        ),
    )

