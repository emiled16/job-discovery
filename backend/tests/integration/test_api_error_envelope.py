from pathlib import Path
import sys

from fastapi import APIRouter
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.api.errors import ApiError  # noqa: E402
from job_discovery_backend.app import create_app  # noqa: E402


def test_error_responses_use_standard_envelope_and_request_id_header() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/api-error")
    def api_error() -> None:
        raise ApiError(409, "conflict", "Duplicate resource")

    app.include_router(router)
    client = TestClient(app)

    response = client.get("/api-error", headers={"X-Request-ID": "req-123"})

    assert response.status_code == 409
    assert response.headers["X-Request-ID"] == "req-123"
    assert response.json() == {
        "error": {
            "code": "conflict",
            "message": "Duplicate resource",
        },
        "request_id": "req-123",
    }


def test_validation_errors_are_returned_with_field_details() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/items/{item_id}")
    def read_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    app.include_router(router)
    client = TestClient(app)

    response = client.get("/items/not-an-int")

    payload = response.json()
    assert response.status_code == 422
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed"
    assert payload["error"]["details"][0]["field"] == "path.item_id"
    assert "X-Request-ID" in response.headers
    assert payload["request_id"] == response.headers["X-Request-ID"]


def test_route_not_found_uses_standard_error_envelope() -> None:
    client = TestClient(create_app())

    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "not_found",
        "message": "Not Found",
    }


def test_unhandled_errors_do_not_leak_internal_details() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/boom")
    def boom() -> None:
        raise RuntimeError("database credentials leaked")

    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_server_error",
        "message": "Internal server error",
    }
