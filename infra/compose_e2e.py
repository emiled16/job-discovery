from __future__ import annotations

import argparse
from dataclasses import dataclass
import time
from uuid import uuid4

import httpx


@dataclass(frozen=True)
class Endpoints:
    frontend_url: str
    api_url: str


def _client(timeout_seconds: int) -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(timeout_seconds), follow_redirects=True)


def _wait_for(client: httpx.Client, url: str, *, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = client.get(url)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {url}")


def _assert_page(client: httpx.Client, url: str, expected_text: str) -> None:
    response = client.get(url)
    response.raise_for_status()
    if expected_text not in response.text:
        raise RuntimeError(f"{url} did not include expected text: {expected_text}")


def _wait_for_run_detail(
    client: httpx.Client,
    frontend_url: str,
    pipeline_run_id: str,
    *,
    timeout_seconds: int,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"{frontend_url}/api/backend/api/v1/admin/pipeline-runs/{pipeline_run_id}",
        )
        response.raise_for_status()
        payload = response.json()["data"]
        if payload["status"] not in {"queued", "running"}:
            return payload
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for pipeline run {pipeline_run_id}")


def run_compose_e2e(endpoints: Endpoints, *, startup_timeout_seconds: int, timeout_seconds: int) -> None:
    with _client(timeout_seconds) as client:
        _wait_for(client, f"{endpoints.api_url}/health", timeout_seconds=startup_timeout_seconds)
        _wait_for(client, endpoints.frontend_url, timeout_seconds=startup_timeout_seconds)

        _assert_page(client, endpoints.frontend_url, "Open dashboard")
        _assert_page(client, f"{endpoints.frontend_url}/dashboard", "Search the live pipeline.")
        _assert_page(client, f"{endpoints.frontend_url}/views", "Reuse the queries that matter.")
        _assert_page(client, f"{endpoints.frontend_url}/summary", "Measure search progress")
        _assert_page(client, f"{endpoints.frontend_url}/admin", "Operate the ingestion surface.")

        jobs_response = client.get(f"{endpoints.frontend_url}/api/backend/api/v1/jobs")
        jobs_response.raise_for_status()
        jobs_payload = jobs_response.json()
        if jobs_payload["meta"]["total"] < 1:
            raise RuntimeError("Expected seeded jobs for compose E2E")

        job_id = jobs_payload["data"][0]["id"]
        application_response = client.put(
            f"{endpoints.frontend_url}/api/backend/api/v1/jobs/{job_id}/application",
            json={"status": "applied"},
        )
        application_response.raise_for_status()

        applications_response = client.get(
            f"{endpoints.frontend_url}/api/backend/api/v1/applications",
            params=[("statuses", "applied")],
        )
        applications_response.raise_for_status()
        if not applications_response.json()["data"]:
            raise RuntimeError("Expected at least one applied job in compose E2E flow")

        view_name = f"Compose Smoke {uuid4().hex[:8]}"
        view_response = client.post(
            f"{endpoints.frontend_url}/api/backend/api/v1/views",
            json={
                "name": view_name,
                "filters": {"title": "Engineer", "location": None, "company_ids": [], "work_modes": [], "posted_after": None, "posted_before": None},
                "sort": {"field": "posted_at", "direction": "desc"},
                "is_default": False,
            },
        )
        view_response.raise_for_status()
        view_id = view_response.json()["data"]["id"]

        summary_response = client.get(f"{endpoints.frontend_url}/api/backend/api/v1/summary/metrics")
        summary_response.raise_for_status()
        summary_payload = summary_response.json()["data"]
        if summary_payload["total_jobs"] < 1 or summary_payload["applied_jobs"] < 1:
            raise RuntimeError("Summary metrics did not reflect seeded/apply flow state")

        companies_response = client.get(f"{endpoints.frontend_url}/api/backend/api/v1/admin/companies")
        companies_response.raise_for_status()
        company_id = companies_response.json()["data"][0]["id"]

        sync_response = client.post(
            f"{endpoints.frontend_url}/api/backend/api/v1/admin/companies/{company_id}/sync",
        )
        sync_response.raise_for_status()
        pipeline_run_id = sync_response.json()["data"]["pipeline_run_id"]

        run_detail = _wait_for_run_detail(
            client,
            endpoints.frontend_url,
            pipeline_run_id,
            timeout_seconds=timeout_seconds,
        )
        if not run_detail["events"]:
            raise RuntimeError("Expected pipeline run events after manual sync")

        delete_response = client.delete(
            f"{endpoints.frontend_url}/api/backend/api/v1/views/{view_id}",
        )
        delete_response.raise_for_status()


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
