"""
Alur autentikasi ujung ke ujung terhadap PostgreSQL sungguhan — Master Schema V2.

Sesi = `user_sessions` (rotasi: baris lama `is_revoked = TRUE`, satu `token_family_id` per perangkat);
percobaan masuk = `app_activity_logs` (`entity_table = 'users'`, `entity_id = login_key(email)`).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.modules.auth.repositories.auth_session_repository import AuthSessionRepository
from tests.conftest import SeededUser, requires_db

pytestmark = requires_db


def _login(client: TestClient, user: SeededUser, password: str | None = None):
    return client.post("/auth/login", json={"email": user.login, "password": password or user.password})


def _refresh(client: TestClient, token: str):
    client.cookies.set("refresh_token", token)
    return client.post("/auth/refresh")


def _attempts(user: SeededUser) -> list[str]:
    key = str(AuthSessionRepository.login_key(user.login))
    return [a for (a,) in user.query(
        "SELECT action FROM app_activity_logs WHERE entity_table = 'users' AND entity_id = %s ORDER BY created_at",
        (key,))]


def _active_sessions(user: SeededUser) -> int:
    return user.query(
        "SELECT count(*) FROM user_sessions WHERE user_id = %s AND NOT is_revoked AND delete_at IS NULL",
        (user.user_id,))[0][0]


def test_login_issues_persisted_session_and_records_attempt(client, seeded_user):
    response = _login(client, seeded_user)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.cookies.get("refresh_token")
    assert _active_sessions(seeded_user) == 1
    assert _attempts(seeded_user) == ["LOGIN_SUCCESS"]


def test_wrong_password_is_rejected_and_failure_is_persisted(client, seeded_user):
    response = _login(client, seeded_user, "salah")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert _attempts(seeded_user) == ["LOGIN_FAILED"]


def test_attempt_log_never_stores_the_login_text(client, seeded_user):
    _login(client, seeded_user, "salah")

    rows = seeded_user.query(
        "SELECT changed_diff::text FROM app_activity_logs WHERE entity_id = %s",
        (str(AuthSessionRepository.login_key(seeded_user.login)),))
    assert rows and all(seeded_user.login not in diff for (diff,) in rows)


def test_five_failures_lock_the_login(client, seeded_user):
    remaining = [_login(client, seeded_user, "salah").json()["error"] for _ in range(5)]
    # Kegagalan 1–4 memberi tahu sisa percobaan; yang ke-5 langsung mengunci & menyebut cooldown.
    assert [e["details"].get("remaining_attempts") for e in remaining[:4]] == [4, 3, 2, 1]
    assert remaining[4]["code"] == "LOCKED"

    response = _login(client, seeded_user)  # kata sandi benar pun ditolak selama cooldown

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "LOCKED"
    assert 14 * 60 < error["details"]["retry_after_seconds"] <= 15 * 60
    assert "15 menit" in error["message"]


def test_unknown_login_is_counted_the_same_way(client):
    """Email tak terdaftar juga terkunci setelah 5 gagal — sisa percobaan tidak membocorkan keberadaan akun."""
    ghost = SeededUser("", "", "tidak-terdaftar-uji@contoh.test", "salah")
    errors = [_login(client, ghost).json()["error"] for _ in range(5)]
    try:
        assert [e["details"].get("remaining_attempts") for e in errors[:4]] == [4, 3, 2, 1]
        assert errors[4]["code"] == "LOCKED"
    finally:
        ghost.query("DELETE FROM app_activity_logs WHERE entity_table = 'users' AND entity_id = %s",
                    (str(AuthSessionRepository.login_key(ghost.login)),))


def test_cooldown_ends_when_the_failures_leave_the_window(client, seeded_user):
    for _ in range(5):
        _login(client, seeded_user, "salah")
    # Mundurkan kegagalan seolah terjadi 20 menit lalu → di luar jendela 15 menit.
    seeded_user.query(
        "UPDATE app_activity_logs SET created_at = now() - interval '20 minutes' "
        "WHERE entity_table = 'users' AND entity_id = %s",
        (str(AuthSessionRepository.login_key(seeded_user.login)),))

    assert _login(client, seeded_user).status_code == 200


def test_successful_login_resets_the_failure_count(client, seeded_user):
    for _ in range(3):
        _login(client, seeded_user, "salah")
    assert _login(client, seeded_user).status_code == 200

    error = _login(client, seeded_user, "salah").json()["error"]

    assert error["details"]["remaining_attempts"] == 4


def test_inactive_account_cannot_log_in(client, seeded_user):
    seeded_user.query("UPDATE users SET is_active = false WHERE user_id = %s", (seeded_user.user_id,))

    response = _login(client, seeded_user)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INACTIVE"


def test_refresh_rotates_token(client, seeded_user):
    first = _login(client, seeded_user).cookies["refresh_token"]

    response = _refresh(client, first)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.cookies["refresh_token"] != first
    rows = seeded_user.query(
        "SELECT is_revoked, token_family_id FROM user_sessions WHERE user_id = %s ORDER BY create_at",
        (seeded_user.user_id,))
    assert [revoked for revoked, _ in rows] == [True, False]   # lama dicabut, baru aktif
    assert len({family for _, family in rows}) == 1             # satu rantai (perangkat) yang sama


def test_reusing_rotated_token_revokes_whole_family(client, seeded_user):
    first = _login(client, seeded_user).cookies["refresh_token"]
    second = _refresh(client, first).cookies["refresh_token"]

    reuse = _refresh(client, first)

    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "SESSION_REVOKED"
    assert _refresh(client, second).status_code == 401
    assert _active_sessions(seeded_user) == 0


def test_refresh_without_cookie_is_401(client):
    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NO_TOKEN"


def test_deactivated_user_cannot_refresh_and_sessions_end(client, seeded_user):
    token = _login(client, seeded_user).cookies["refresh_token"]
    seeded_user.query("UPDATE users SET is_active = false WHERE user_id = %s", (seeded_user.user_id,))

    response = _refresh(client, token)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INACTIVE"
    assert _active_sessions(seeded_user) == 0


def test_logout_revokes_session(client, seeded_user):
    token = _login(client, seeded_user).cookies["refresh_token"]
    client.cookies.set("refresh_token", token)

    assert client.post("/auth/logout").status_code == 200
    assert _refresh(client, token).status_code == 401


def test_me_returns_current_user(client, seeded_user):
    access = _login(client, seeded_user).json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == seeded_user.user_id
    assert body["email"] == seeded_user.login
    assert body["role"] == "SUPER_ADMIN"
    assert body["attendance_mode"] == "OFFICE"
    assert isinstance(body["permissions"], list)


def test_change_password_rejects_wrong_current_password(client, seeded_user):
    access = _login(client, seeded_user).json()["access_token"]

    response = client.post(
        "/auth/change-password",
        json={"current_password": "salah", "new_password": "KataSandiBaru-456"},
        headers={"Authorization": f"Bearer {access}"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["fields"]["current_password"]


def test_change_password_rejects_same_as_old_password(client, seeded_user):
    access = _login(client, seeded_user).json()["access_token"]

    response = client.post(
        "/auth/change-password",
        json={"current_password": seeded_user.password, "new_password": seeded_user.password},
        headers={"Authorization": f"Bearer {access}"},
    )

    assert response.status_code == 422
    fields = response.json()["error"]["details"]["fields"]
    assert fields["new_password"] == "Sandi baru tidak boleh sama dengan sandi lama."
    assert _login(client, seeded_user).status_code == 200


def test_change_password_rotates_all_sessions(client, seeded_user):
    login = _login(client, seeded_user)
    old_refresh = login.cookies["refresh_token"]

    response = client.post(
        "/auth/change-password",
        json={"current_password": seeded_user.password, "new_password": "KataSandiBaru-456"},
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 200
    new_refresh = response.cookies["refresh_token"]
    assert _refresh(client, old_refresh).status_code == 401
    assert _refresh(client, new_refresh).status_code == 200
    assert _login(client, seeded_user, "KataSandiBaru-456").status_code == 200


def test_unknown_login_still_runs_password_hash(monkeypatch):
    """Login tak terdaftar tetap memverifikasi argon2 (hash tiruan) — waktu respons tidak membocorkan
    email mana yang terdaftar."""
    import asyncio

    from app.modules.auth.services import auth_service as svc

    calls: list[str] = []
    monkeypatch.setattr(svc, "verify_password", lambda pw, h: calls.append(h) or False)

    class _Users:
        async def find_by_login(self, login: str) -> None:
            return None

    class _Sessions:
        async def failed_logins(self, login: str) -> object:
            from types import SimpleNamespace
            return SimpleNamespace(failures=1, locked_until=None, retry_after_seconds=0)

        async def record_login_attempt(self, *a: object, **k: object) -> None:
            return None

    service = svc.AuthService(_Users(), _Sessions())  # type: ignore[arg-type]
    with pytest.raises(svc.AppError) as err:
        asyncio.run(service.login("tidak-ada@contoh.id", "salah", svc.ClientInfo(ip=None, user_agent="uji")))
    assert err.value.code == "INVALID_CREDENTIALS"
    assert len(calls) == 1 and calls[0].startswith("$argon2")
