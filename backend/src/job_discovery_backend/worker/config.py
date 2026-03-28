from dataclasses import dataclass
import os
from typing import Mapping
from urllib.parse import urlparse


class ConfigError(ValueError):
    """Raised when worker configuration is invalid."""


@dataclass(frozen=True)
class WorkerSettings:
    broker_url: str
    result_backend: str
    database_url: str
    max_company_sync_workers: int


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


def _parse_positive_int(env: Mapping[str, str], key: str, default: str) -> int:
    raw_value = env.get(key, default).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a positive integer") from exc

    if value <= 0:
        raise ConfigError(f"{key} must be a positive integer")

    return value


def load_settings(env: Mapping[str, str] | None = None) -> WorkerSettings:
    source = os.environ if env is None else env

    return WorkerSettings(
        broker_url=_parse_url(
            source,
            "WORKER_BROKER_URL",
            "redis://redis:6379/0",
            {"redis", "rediss"},
        ),
        result_backend=_parse_url(
            source,
            "WORKER_RESULT_BACKEND",
            "redis://redis:6379/1",
            {"redis", "rediss"},
        ),
        database_url=_parse_url(
            source,
            "WORKER_DATABASE_URL",
            "postgresql://job_discovery:job_discovery@postgres:5432/job_discovery",
            {"sqlite", "postgres", "postgresql"},
        ),
        max_company_sync_workers=_parse_positive_int(
            source,
            "WORKER_MAX_COMPANY_SYNC_WORKERS",
            "4",
        ),
    )
