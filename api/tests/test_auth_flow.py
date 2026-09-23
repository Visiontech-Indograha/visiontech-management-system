"""
Alur autentikasi ujung ke ujung terhadap PostgreSQL sungguhan (P1-1, P1-2, DoD fase 1).
Bentuk respons dan kode galat dijaga sama dengan perilaku sebelum refactor A-2.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import SeededUser, requires_db

pytestmark = requires_db


def _login(client: TestClient, user: SeededUser, password: str | None = None):
    return client.post("/auth/login", json={"email": user.login, "password": password or user.password})


def _refresh(client: TestClient, token: str):
    client.cookies.set("refresh_token", token)
    return client.post("/auth/refresh")


def test_login_issues_persisted_session_and_records_attempt(client, seeded_user):
    response = _login(client, seeded_user)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.cookies.get("refresh_token")
    assert seeded_user.query(
        "SELECT state FROM vms.user_session WHERE user_id = %s", (seeded_user.user_id,)
    ) == [("ACTIVE",)]
    assert seeded_user.query(
        "SELECT successful FROM vms.login_attempt WHERE login = %s", (seeded_user.login,)
    ) == [(True,)]


def test_wrong_password_is_rejected_and_failure_is_persisted(client, seeded_user):
    response = _login(client, seeded_user, "salah")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert seeded_user.query(
        "SELECT successful FROM vms.login_attempt WHERE login = %s", (seeded_user.login,)
    ) == [(False,)]


def test_five_failures_lock_the_login(client, seeded_user):
    for _ in range(5):
        _login(client, seeded_user, "salah")

    response = _login(client, seeded_user)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "LOCKED"


def test_inactive_account_cannot_log_in(client, seeded_user):
    seeded_user.query("UPDATE vms.app_user SET is_active = false WHERE id = %s", (seeded_user.user_id,))

    response = _login(client, seeded_user)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INACTIVE"


def test_refresh_rotates_token(client, seeded_user):
    first = _login(client, seeded_user).cookies["refresh_token"]

    response = _refresh(client, first)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.cookies["refresh_token"] != first
    states = sorted(s for (s,) in seeded_user.query(
        "SELECT state::text FROM vms.user_session WHERE user_id = %s", (seeded_user.user_id,)
    ))
    assert states == ["ACTIVE", "ROTATED"]


def test_reusing_rotated_token_revokes_whole_family(client, seeded_user):
    first = _login(client, seeded_user).cookies["refresh_token"]
    second = _refresh(client, first).cookies["refresh_token"]

    reuse = _refresh(client, first)

    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "SESSION_REVOKED"
    assert _refresh(client, second).status_code == 401
    assert seeded_user.query(
        "SELECT count(*) FROM vms.user_session WHERE user_id = %s AND state = 'ACTIVE'", (seeded_user.user_id,)
    ) == [(0,)]


def test_refresh_without_cookie_is_401(client):
    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NO_TOKEN"


def test_deactivated_user_cannot_refresh_and_sessions_end(client, seeded_user):
    token = _login(client, seeded_user).cookies["refresh_token"]
    seeded_user.query("UPDATE vms.app_user SET is_active = false WHERE id = %s", (seeded_user.user_id,))

    response = _refresh(client, token)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INACTIVE"
    assert seeded_user.query(
        "SELECT count(*) FROM vms.user_session WHERE user_id = %s AND state = 'ACTIVE'", (seeded_user.user_id,)
    ) == [(0,)]


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
    assert body["role"] == "ADMIN"
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
