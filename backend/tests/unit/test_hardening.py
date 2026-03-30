from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.api.validation import validate_http_url  # noqa: E402
from job_discovery_backend.ingestion.adapters.base import fetch_json, fetch_text  # noqa: E402
from job_discovery_backend.ingestion.models import IngestionError  # noqa: E402
from job_discovery_backend.observability import JsonFormatter, clear_request_id, set_request_id  # noqa: E402
from job_discovery_backend.worker.config import load_settings  # noqa: E402


def test_structured_logging_includes_service_request_id_and_message() -> None:
    formatter = JsonFormatter(service_name="api")
    token = set_request_id("req-123")
    try:
        record = __import__("logging").LogRecord(
            name="job_discovery.test",
            level=20,
            pathname=__file__,
            lineno=10,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        payload = formatter.format(record)
    finally:
        clear_request_id(token)

    assert '"service":"api"' in payload
    assert '"request_id":"req-123"' in payload
    assert '"message":"hello world"' in payload


@pytest.mark.parametrize(
    "value",
    [
        "http://127.0.0.1/test",
        "https://localhost/admin",
        "https://user:pass@example.com/jobs",
        "https://internal",
    ],
)
def test_public_http_url_validation_rejects_unsafe_targets(value: str) -> None:
    with pytest.raises(ValueError):
        validate_http_url(value, field_name="website_url")


def test_fetch_json_rejects_unsafe_urls_before_request() -> None:
    with pytest.raises(IngestionError, match="request_url must target a public hostname"):
        fetch_json("http://127.0.0.1/jobs", timeout_seconds=5)


def test_fetch_text_rejects_unsafe_urls_before_request() -> None:
    with pytest.raises(IngestionError, match="request_url must target a public hostname"):
        fetch_text("http://127.0.0.1/jobs", timeout_seconds=5)


def test_fetch_json_surfaces_timeout_fail_fast() -> None:
    with patch("job_discovery_backend.ingestion.adapters.base.httpx.Client") as client_class:
        client = client_class.return_value.__enter__.return_value
        client.get.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(IngestionError, match="timed out after 5 seconds"):
            fetch_json("https://boards-api.greenhouse.io/v1/boards/openai/jobs", timeout_seconds=5)


def test_worker_http_timeout_setting_must_be_positive() -> None:
    with pytest.raises(ValueError, match="WORKER_HTTP_TIMEOUT_SECONDS must be a positive integer"):
        load_settings({"WORKER_HTTP_TIMEOUT_SECONDS": "0"})
