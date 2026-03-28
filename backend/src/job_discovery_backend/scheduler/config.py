from dataclasses import dataclass
import os
from typing import Mapping
from urllib.parse import urlparse


class ConfigError(ValueError):
    """Raised when scheduler configuration is invalid."""


@dataclass(frozen=True)
class SchedulerSettings:
    broker_url: str
    result_backend: str
    sync_interval_seconds: int
    timezone: str


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


def _require_text(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key, default).strip()
    if not value:
        raise ConfigError(f"{key} must not be empty")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> SchedulerSettings:
    source = os.environ if env is None else env

    return SchedulerSettings(
        broker_url=_parse_url(
            source,
            "SCHEDULER_BROKER_URL",
            "redis://redis:6379/0",
            {"redis", "rediss"},
        ),
        result_backend=_parse_url(
            source,
            "SCHEDULER_RESULT_BACKEND",
            "redis://redis:6379/1",
            {"redis", "rediss"},
        ),
        sync_interval_seconds=_parse_positive_int(
            source,
            "SCHEDULER_SYNC_INTERVAL_SECONDS",
            "14400",
        ),
        timezone=_require_text(source, "SCHEDULER_TIMEZONE", "UTC"),
    )
