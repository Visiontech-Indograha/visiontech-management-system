from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import AppError, ConflictError, NotFoundError, app_error_handler


def _client(exc: AppError) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]

    @app.get("/boom")
    async def boom():
        raise exc

    return TestClient(app)


def test_app_error_uses_contract_shape():
    exc = AppError(
        "PLAN_NOT_ACCEPTED",
        "Pekerjaan belum diterima ketua tim, jadi belum bisa dimulai.",
        status=409,
        details={"status": "PUBLISHED"},
    )
    response = _client(exc).get("/boom")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "PLAN_NOT_ACCEPTED",
            "message": "Pekerjaan belum diterima ketua tim, jadi belum bisa dimulai.",
            "details": {"status": "PUBLISHED"},
        }
    }


def test_details_default_to_empty_object():
    response = _client(NotFoundError("Pekerjaan")).get("/boom")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "NOT_FOUND",
        "message": "Pekerjaan tidak ditemukan.",
        "details": {},
    }


def test_conflict_error_is_409_with_reload_message():
    response = _client(ConflictError()).get("/boom")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert "Muat ulang" in response.json()["error"]["message"]
