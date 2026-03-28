from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


@dataclass(frozen=True)
class Endpoints:
    frontend_url: str
    api_url: str


def _request(
    url: str,
    *,
    method: str = "GET",
    timeout_seconds: int,
    params: list[tuple[str, str]] | None = None,
    json_body: dict | None = None,
) -> tuple[int, dict[str, str], str]:
    if params:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{urlencode(params, doseq=True)}"

    body_bytes: bytes | None = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        body_bytes = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body_bytes, headers=headers, method=method)
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.status, dict(response.headers), response.read().decode("utf-8")


def _request_json(
    url: str,
    *,
    method: str = "GET",
    timeout_seconds: int,
    params: list[tuple[str, str]] | None = None,
    json_body: dict | None = None,
) -> dict:
    status, _headers, body = _request(
        url,
        method=method,
        timeout_seconds=timeout_seconds,
        params=params,
        json_body=json_body,
    )
    if status >= 400:
        raise RuntimeError(f"{method} {url} failed with status {status}")
    return json.loads(body)


def _wait_for(url: str, *, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            status, _, _ = _request(url, timeout_seconds=timeout_seconds)
            if status == 200:
                return
        except (HTTPError, URLError):
            pass
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {url}")


def _assert_page(url: str, expected_text: str, *, timeout_seconds: int) -> None:
    status, _, body = _request(url, timeout_seconds=timeout_seconds)
    if status >= 400:
        raise RuntimeError(f"{url} failed with status {status}")
    if expected_text not in body:
        raise RuntimeError(f"{url} did not include expected text: {expected_text}")


def _wait_for_run_detail(
    frontend_url: str,
    pipeline_run_id: str,
    *,
    timeout_seconds: int,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        payload = _request_json(
            f"{frontend_url}/api/backend/api/v1/admin/pipeline-runs/{pipeline_run_id}",
            timeout_seconds=timeout_seconds,
        )
        payload = payload["data"]
        if payload["status"] not in {"queued", "running"}:
            return payload
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for pipeline run {pipeline_run_id}")


def run_compose_e2e(endpoints: Endpoints, *, startup_timeout_seconds: int, timeout_seconds: int) -> None:
    _wait_for(f"{endpoints.api_url}/health", timeout_seconds=startup_timeout_seconds)
    _wait_for(endpoints.frontend_url, timeout_seconds=startup_timeout_seconds)

    _assert_page(endpoints.frontend_url, "Open dashboard", timeout_seconds=timeout_seconds)
    _assert_page(
        f"{endpoints.frontend_url}/dashboard",
        "Search the live pipeline.",
        timeout_seconds=timeout_seconds,
    )
    _assert_page(
        f"{endpoints.frontend_url}/views",
        "Reuse the queries that matter.",
        timeout_seconds=timeout_seconds,
    )
    _assert_page(
        f"{endpoints.frontend_url}/summary",
        "Measure search progress",
        timeout_seconds=timeout_seconds,
    )
    _assert_page(
        f"{endpoints.frontend_url}/admin",
        "Operate the ingestion surface.",
        timeout_seconds=timeout_seconds,
    )

    jobs_payload = _request_json(
        f"{endpoints.frontend_url}/api/backend/api/v1/jobs",
        timeout_seconds=timeout_seconds,
    )
    if jobs_payload["meta"]["total"] < 1:
        raise RuntimeError("Expected seeded jobs for compose E2E")

    job_id = jobs_payload["data"][0]["id"]
    _request_json(
        f"{endpoints.frontend_url}/api/backend/api/v1/jobs/{job_id}/application",
        method="PUT",
        json_body={"status": "applied"},
        timeout_seconds=timeout_seconds,
    )

    applications_payload = _request_json(
        f"{endpoints.frontend_url}/api/backend/api/v1/applications",
        params=[("statuses", "applied")],
        timeout_seconds=timeout_seconds,
    )
    if not applications_payload["data"]:
        raise RuntimeError("Expected at least one applied job in compose E2E flow")

    view_name = f"Compose Smoke {uuid4().hex[:8]}"
    view_payload = _request_json(
        f"{endpoints.frontend_url}/api/backend/api/v1/views",
        method="POST",
        json_body={
            "name": view_name,
            "filters": {
                "title": "Engineer",
                "location": None,
                "company_ids": [],
                "work_modes": [],
                "posted_after": None,
                "posted_before": None,
            },
            "sort": {"field": "posted_at", "direction": "desc"},
            "is_default": False,
        },
        timeout_seconds=timeout_seconds,
    )
    view_id = view_payload["data"]["id"]

    summary_payload = _request_json(
        f"{endpoints.frontend_url}/api/backend/api/v1/summary/metrics",
        timeout_seconds=timeout_seconds,
    )["data"]
    if summary_payload["total_jobs"] < 1 or summary_payload["applied_jobs"] < 1:
        raise RuntimeError("Summary metrics did not reflect seeded/apply flow state")

    companies_payload = _request_json(
        f"{endpoints.frontend_url}/api/backend/api/v1/admin/companies",
        timeout_seconds=timeout_seconds,
    )
    company_id = companies_payload["data"][0]["id"]

    sync_payload = _request_json(
        f"{endpoints.frontend_url}/api/backend/api/v1/admin/companies/{company_id}/sync",
        method="POST",
        timeout_seconds=timeout_seconds,
    )
    pipeline_run_id = sync_payload["data"]["pipeline_run_id"]

    run_detail = _wait_for_run_detail(
        endpoints.frontend_url,
        pipeline_run_id,
        timeout_seconds=timeout_seconds,
    )
    if not run_detail["events"]:
        raise RuntimeError("Expected pipeline run events after manual sync")

    delete_status, _, _ = _request(
        f"{endpoints.frontend_url}/api/backend/api/v1/views/{view_id}",
        method="DELETE",
        timeout_seconds=timeout_seconds,
    )
    if delete_status != 204:
        raise RuntimeError(f"Expected 204 deleting smoke saved view, got {delete_status}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run compose-backed smoke coverage against the live stack.")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:3000")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--startup-timeout-seconds", type=int, default=120)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    args = parser.parse_args()

    run_compose_e2e(
        Endpoints(frontend_url=args.frontend_url.rstrip("/"), api_url=args.api_url.rstrip("/")),
        startup_timeout_seconds=args.startup_timeout_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    print("Compose E2E passed.")


if __name__ == "__main__":
    main()
