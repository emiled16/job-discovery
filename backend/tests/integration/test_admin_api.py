from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session

from support.api import api_client, migrated_sqlite_engine, session_for_database  # noqa: E402
from support.records import seed_company, seed_company_source, seed_pipeline_run, seed_pipeline_run_event, seed_user  # noqa: E402

from job_discovery_backend.db.models import PipelineRun  # noqa: E402


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'admin-api.sqlite3'}"


def test_admin_companies_list_and_create_validate_defaults(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        seed_user(session)
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222221",
            slug="openai",
            name="OpenAI",
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333331",
            company_id=company.id,
        )

    with api_client(database_url) as client:
        listed = client.get("/api/v1/admin/companies")
        created = client.post(
            "/api/v1/admin/companies",
            json={
                "slug": "vercel",
                "name": "Vercel",
                "source": {"source_type": "lever", "base_url": "https://jobs.lever.co/vercel"},
            },
        )
        invalid = client.post(
            "/api/v1/admin/companies",
            json={"slug": "broken", "source": {"source_type": "lever"}},
        )

    assert listed.status_code == 200
    assert listed.json()["data"][0]["name"] == "OpenAI"
    assert created.status_code == 201
    assert created.json()["data"]["lifecycle_status"] == "draft"
    assert created.json()["data"]["sources"][0]["is_enabled"] is True
    assert invalid.status_code == 422


def test_admin_company_patch_validates_lifecycle_transitions(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        active = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222222",
            slug="openai",
            name="OpenAI",
            lifecycle_status="active",
        )
        archived = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222223",
            slug="archived",
            name="Archived",
            lifecycle_status="archived",
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333332",
            company_id=active.id,
        )
        seed_company_source(
            session,
            source_id="33333333-3333-3333-3333-333333333333",
            company_id=archived.id,
        )

    with api_client(database_url) as client:
        valid = client.patch(
            f"/api/v1/admin/companies/{active.id}",
            json={"lifecycle_status": "paused", "source": {"is_enabled": False}},
        )
        invalid = client.patch(
            f"/api/v1/admin/companies/{archived.id}",
            json={"lifecycle_status": "active"},
        )

    assert valid.status_code == 200
    assert valid.json()["data"]["lifecycle_status"] == "paused"
    assert valid.json()["data"]["sources"][0]["is_enabled"] is False
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_state_transition"


def test_manual_sync_dispatches_company_request_metadata(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        user = seed_user(session)
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222224",
            slug="openai",
            name="OpenAI",
        )

    with patch("job_discovery_backend.api.routes.v1.admin.dispatch_company_sync") as dispatch:
        with api_client(database_url) as client:
            response = client.post(
                f"/api/v1/admin/companies/{company.id}/sync",
                headers={"X-Request-ID": "req-sync-1"},
            )

    assert response.status_code == 202
    pipeline_run_id = response.json()["data"]["pipeline_run_id"]
    assert response.json()["data"] == {
        "task_name": "pipeline.sync_company",
        "company_id": company.id,
        "pipeline_run_id": pipeline_run_id,
        "request_id": "req-sync-1",
        "status": "queued",
    }
    dispatch.assert_called_once_with(
        {
            "pipeline_run_id": pipeline_run_id,
            "company_id": company.id,
            "requested_by_user_id": user.id,
            "request_id": "req-sync-1",
            "trigger_type": "manual",
        }
    )

    engine = migrated_sqlite_engine(database_url)
    with Session(engine) as session:
        run = session.get(PipelineRun, pipeline_run_id)
        assert run is not None
        assert run.company_id == company.id
        assert run.status == "queued"
    engine.dispose()


def test_pipeline_runs_list_filters_by_status_date_and_company(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        user = seed_user(session)
        openai = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222225",
            slug="openai",
            name="OpenAI",
        )
        other = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222226",
            slug="vercel",
            name="Vercel",
        )
        seed_pipeline_run(
            session,
            run_id="77777777-7777-7777-7777-777777777771",
            company_id=openai.id,
            user_id=user.id,
            trigger_type="manual",
            status="failed",
            started_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
        )
        seed_pipeline_run(
            session,
            run_id="77777777-7777-7777-7777-777777777772",
            company_id=openai.id,
            user_id=user.id,
            trigger_type="scheduled",
            status="succeeded",
            started_at=datetime(2026, 2, 2, 10, 0, tzinfo=UTC),
        )
        seed_pipeline_run(
            session,
            run_id="77777777-7777-7777-7777-777777777773",
            company_id=other.id,
            user_id=user.id,
            trigger_type="manual",
            status="failed",
            started_at=datetime(2026, 2, 3, 10, 0, tzinfo=UTC),
        )

    with api_client(database_url) as client:
        response = client.get(
            "/api/v1/admin/pipeline-runs",
            params=[
                ("company_id", openai.id),
                ("statuses", "failed"),
                ("started_after", "2026-02-01"),
                ("started_before", "2026-02-28"),
            ],
        )

    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1
    assert response.json()["data"][0]["id"] == "77777777-7777-7777-7777-777777777771"


def test_pipeline_run_detail_returns_joined_event_payloads(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        user = seed_user(session)
        company = seed_company(
            session,
            company_id="22222222-2222-2222-2222-222222222227",
            slug="openai",
            name="OpenAI",
        )
        run = seed_pipeline_run(
            session,
            run_id="77777777-7777-7777-7777-777777777774",
            company_id=company.id,
            user_id=user.id,
            trigger_type="manual",
            status="failed",
            request_id="req-run-1",
            started_at=datetime(2026, 2, 10, 10, 0, tzinfo=UTC),
        )
        seed_pipeline_run_event(
            session,
            event_id="88888888-8888-8888-8888-888888888881",
            pipeline_run_id=run.id,
            company_id=company.id,
            event_type="fetch.started",
            level="info",
            sequence_number=1,
            message="Fetch started",
            payload={"step": "fetch"},
        )
        seed_pipeline_run_event(
            session,
            event_id="88888888-8888-8888-8888-888888888882",
            pipeline_run_id=run.id,
            company_id=company.id,
            event_type="fetch.failed",
            level="error",
            sequence_number=2,
            message="Fetch failed",
            payload={"error": "timeout"},
        )

    with api_client(database_url) as client:
        response = client.get(f"/api/v1/admin/pipeline-runs/{run.id}")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == run.id
    assert payload["company"]["name"] == "OpenAI"
    assert payload["events"] == [
        {
            "id": "88888888-8888-8888-8888-888888888881",
            "company_id": company.id,
            "event_type": "fetch.started",
            "level": "info",
            "sequence_number": 1,
            "message": "Fetch started",
            "payload": {"step": "fetch"},
            "created_at": payload["events"][0]["created_at"],
        },
        {
            "id": "88888888-8888-8888-8888-888888888882",
            "company_id": company.id,
            "event_type": "fetch.failed",
            "level": "error",
            "sequence_number": 2,
            "message": "Fetch failed",
            "payload": {"error": "timeout"},
            "created_at": payload["events"][1]["created_at"],
        },
    ]
