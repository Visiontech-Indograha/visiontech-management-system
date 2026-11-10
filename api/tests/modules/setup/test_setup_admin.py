"""Penyiapan awal (POST /setup/admin): kode env, kunci permanen, konkurensi, rate limit, audit.

DB uji dipakai bersama tes lain (sudah ada SUPER_ADMIN lain), jadi pemeriksaan "belum ada admin" dalam tes ini
dipersempit ke akun uji berawalan `setup-test-` (kunci advisory, transaksi, dan INSERT tetap yang asli).
"""
from __future__ import annotations

import secrets

import pytest

from app.core.config import settings
from app.core.rate_limit import GROUP_SETUP, TokenBucketLimiter, set_limiter
from app.modules.setup.repositories.setup_repository import SetupRepository
from tests.concurrency import dua_bersamaan
from tests.conftest import requires_db, sync_query

pytestmark = requires_db

# Nilai acak per proses uji (tidak ada rahasia/contoh rahasia di kode).
TOKEN = secrets.token_urlsafe(24)
WRONG_TOKEN = secrets.token_urlsafe(24)
PASSWORD = secrets.token_urlsafe(18)
PREFIX = f"setup-test-{secrets.token_hex(4)}-"  # unik per proses xdist: worker lain tidak saling menghapus


def _body(n: int = 1, token: str = TOKEN) -> dict:
    return {"setup_token": token, "full_name": "Admin Uji Setup", "email": f"{PREFIX}{n}@example.com",
            "password": PASSWORD}


def _cleanup() -> None:
    rows = sync_query("SELECT user_id::text, employee_id::text FROM users WHERE starts_with(email, %s)", (PREFIX,))
    for uid, _ in rows:
        sync_query("DELETE FROM app_activity_logs WHERE entity_id = %s", (uid,))
        sync_query("DELETE FROM user_sessions WHERE user_id = %s", (uid,))
    sync_query("DELETE FROM users WHERE starts_with(email, %s)", (PREFIX,))
    for _, emp in rows:
        sync_query("DELETE FROM employee WHERE employee_id = %s", (emp,))


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SETUP_TOKEN", TOKEN)

    async def only_test_admins(self: SetupRepository) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM users WHERE system_role = 'SUPER_ADMIN' AND is_active = true "
            "AND delete_at IS NULL AND starts_with(email, :p))", {"p": PREFIX}))

    monkeypatch.setattr(SetupRepository, "has_active_super_admin", only_test_admins)
    set_limiter(None)
    _cleanup()
    yield
    set_limiter(None)
    _cleanup()


def test_status_is_public(client):
    r = client.get("/setup/status")
    assert r.status_code == 200
    assert r.json() == {"needs_setup": True, "enabled": True}


def test_disabled_without_token_is_404(client, monkeypatch):
    monkeypatch.setattr(settings, "SETUP_TOKEN", "")
    assert client.post("/setup/admin", json=_body()).status_code == 404
    monkeypatch.setattr(settings, "SETUP_TOKEN", "pendek")
    assert client.post("/setup/admin", json=_body(token="pendek")).status_code == 404
    assert client.get("/setup/status").json()["enabled"] is False


def test_wrong_token_is_403_and_creates_nothing(client):
    r = client.post("/setup/admin", json=_body(token=WRONG_TOKEN))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "SETUP_TOKEN_INVALID"
    assert sync_query("SELECT 1 FROM users WHERE starts_with(email, %s)", (PREFIX,)) == []


def test_weak_input_is_422(client):
    body = _body()
    body["password"] = "pendek"
    assert client.post("/setup/admin", json=body).status_code == 422


def test_creates_admin_then_locks_forever_and_audits(client):
    r = client.post("/setup/admin", json=_body(1))
    assert r.status_code == 201, r.text
    user_id = r.json()["user_id"]
    assert "password" not in r.text
    again = client.post("/setup/admin", json=_body(2))
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "SETUP_LOCKED"
    assert client.get("/setup/status").json()["needs_setup"] is False
    login = client.post("/auth/login", json={"email": f"{PREFIX}1@example.com", "password": PASSWORD})
    assert login.status_code == 200, login.text
    role = sync_query("SELECT system_role::text FROM users WHERE user_id = %s", (user_id,))
    assert role == [("SUPER_ADMIN",)]
    audit = sync_query("SELECT action FROM app_activity_logs WHERE entity_id = %s", (user_id,))
    assert ("SETUP_ADMIN_CREATED",) in audit


def test_two_simultaneous_requests_create_exactly_one_admin(client):
    results = dua_bersamaan(lambda i: client.post("/setup/admin", json=_body(i + 1)))
    assert sorted(r.status_code for r in results) == [201, 409], [r.text for r in results]
    assert len(sync_query("SELECT 1 FROM users WHERE starts_with(email, %s)", (PREFIX,))) == 1


def test_rate_limit_is_always_enforced(client):
    set_limiter(TokenBucketLimiter({GROUP_SETUP: 2, "auth": 30, "file_url": 30, "upload": 30, "face": 30}))
    assert settings.RATE_LIMIT_ENFORCE is False
    codes = [client.get("/setup/status").status_code for _ in range(3)]
    assert codes == [200, 200, 429]
