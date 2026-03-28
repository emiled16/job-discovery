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
    )
