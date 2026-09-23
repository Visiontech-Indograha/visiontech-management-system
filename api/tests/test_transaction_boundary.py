"""
T-02 · Batas transaksi bawaan: satu permintaan = satu transaksi (dok 12).
Endpoint sukses → data tersimpan; endpoint gagal → tidak ada sisa; commit gagal → klien
menerima 500, bukan 200 (commit terjadi sebelum respons dikirim).
"""
from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB_SCOPE, get_db
from app.core.errors import AppError, app_error_handler
from tests.conftest import requires_db, sync_query

pytestmark = requires_db


@pytest.fixture
def org_name() -> Iterator[str]:
    name = f"uji-t02-{uuid.uuid4().hex[:10]}"
    yield name
    sync_query("DELETE FROM vms.organization WHERE name = %s", (name,))


def _app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]

    async def insert(db: AsyncSession, name: str) -> None:
        await db.execute(text("INSERT INTO vms.organization (name) VALUES (:n)"), {"n": name})

    @app.post("/ok/{name}")
    async def ok(name: str, db: AsyncSession = Depends(get_db, scope=DB_SCOPE)) -> dict[str, str]:
        await insert(db, name)
        return {"status": "ok"}

    @app.post("/http-error/{name}")
    async def http_error(name: str, db: AsyncSession = Depends(get_db, scope=DB_SCOPE)) -> None:
        await insert(db, name)
        raise HTTPException(status_code=400, detail="gagal")

    @app.post("/app-error-persist/{name}")
    async def app_error_persist(name: str, db: AsyncSession = Depends(get_db, scope=DB_SCOPE)) -> None:
        await insert(db, name)
        raise AppError("DITOLAK_TAPI_DICATAT", "Ditolak.", status=403, persist=True)

    return app


def _count(name: str) -> int:
    return sync_query("SELECT count(*) FROM vms.organization WHERE name = %s", (name,))[0][0]


def test_successful_request_commits(org_name):
    with TestClient(_app()) as client:
        assert client.post(f"/ok/{org_name}").status_code == 200

    assert _count(org_name) == 1


def test_failed_request_rolls_back(org_name):
    with TestClient(_app()) as client:
        assert client.post(f"/http-error/{org_name}").status_code == 400

    assert _count(org_name) == 0


def test_persisting_app_error_still_commits(org_name):
    with TestClient(_app()) as client:
        assert client.post(f"/app-error-persist/{org_name}").status_code == 403

    assert _count(org_name) == 1


def test_commit_failure_is_reported_to_client(org_name, monkeypatch):
    async def failing_commit(self: AsyncSession) -> None:
        raise RuntimeError("commit gagal")

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    with TestClient(_app(), raise_server_exceptions=False) as client:
        response = client.post(f"/ok/{org_name}")

    assert response.status_code == 500
    assert _count(org_name) == 0
