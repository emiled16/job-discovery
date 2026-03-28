from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.db.models import SavedView  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from support.api import api_client, session_for_database  # noqa: E402
from support.records import seed_saved_view, seed_user  # noqa: E402


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'views-api.sqlite3'}"


def _valid_view_payload(name: str = "Remote ML") -> dict:
    return {
        "name": name,
        "filters": {
            "title": "ML Engineer",
            "location": "Toronto",
            "company_ids": ["company-1"],
            "work_modes": ["remote"],
            "posted_after": "2026-01-01",
            "posted_before": "2026-01-31",
        },
        "sort": {"field": "posted_at", "direction": "desc"},
        "is_default": False,
    }


def test_saved_view_create_validates_contract(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        seed_user(session)

    with api_client(database_url) as client:
        created = client.post("/api/v1/views", json=_valid_view_payload())
        invalid = client.post(
            "/api/v1/views",
            json={
                **_valid_view_payload("Broken"),
                "filters": {**_valid_view_payload()["filters"], "work_modes": ["space"]},
            },
        )

    assert created.status_code == 201
    assert created.json()["data"]["name"] == "Remote ML"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_saved_view_read_and_list_respect_ownership(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    with session_for_database(database_url) as session:
        local_user = seed_user(session)
        other_user = seed_user(
            session,
            user_id="11111111-1111-1111-1111-111111111112",
            seed_key="other_user",
            display_name="Other User",
        )
        own_view = seed_saved_view(
            session,
            view_id="66666666-6666-6666-6666-666666666661",
            user_id=local_user.id,
            name="Own View",
            filters={"title": "ML"},
            sort={"field": "posted_at", "direction": "desc"},
        )
        other_view = seed_saved_view(
            session,
            view_id="66666666-6666-6666-6666-666666666662",
            user_id=other_user.id,
            name="Other View",
            filters={"title": "Backend"},
            sort={"field": "posted_at", "direction": "desc"},
        )

    with api_client(database_url) as client:
        listed = client.get("/api/v1/views")
        own_response = client.get(f"/api/v1/views/{own_view.id}")
        other_response = client.get(f"/api/v1/views/{other_view.id}")

    assert listed.status_code == 200
    assert [view["id"] for view in listed.json()["data"]] == [own_view.id]
    assert own_response.status_code == 200
    assert own_response.json()["data"]["name"] == "Own View"
    assert other_response.status_code == 404
