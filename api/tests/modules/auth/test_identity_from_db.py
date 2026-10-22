"""
T-04 · Peran & status akun dibaca dari basis data pada setiap permintaan (dok 05 §4).
Access token hanya membawa identitas; mengubah `users.system_role` atau menonaktifkan akun berlaku pada
permintaan berikutnya, tanpa menunggu token kedaluwarsa.
"""
from __future__ import annotations

from app.core.security import verify_jwt_token
from tests.conftest import login_headers, requires_db

pytestmark = requires_db


def test_access_token_carries_identity_only(client, make_user):
    user = make_user("ADMIN")
    token = login_headers(client, user)["Authorization"].removeprefix("Bearer ")

    claims = verify_jwt_token(token)

    assert claims["sub"] == user.user_id
    assert claims["org"] == user.org_id
    assert claims["jti"]
    assert "role" not in claims and "roles" not in claims and "permissions" not in claims


def test_demoted_role_takes_effect_on_next_request(client, make_user):
    user = make_user("OPS")
    headers = login_headers(client, user)
    assert client.get("/audit-events", headers=headers).status_code == 200

    user.query("UPDATE users SET system_role = 'ADMIN_HR_GA' WHERE user_id = %s", (user.user_id,))

    assert client.get("/audit-events", headers=headers).status_code == 403


def test_promoted_role_takes_effect_without_new_login(client, make_user):
    user = make_user("HR")
    headers = login_headers(client, user)
    assert client.get("/audit-events", headers=headers).status_code == 403

    user.query("UPDATE users SET system_role = 'OPERATIONAL_MANAGER' WHERE user_id = %s", (user.user_id,))

    assert client.get("/audit-events", headers=headers).status_code == 200


def test_permissions_follow_the_system_role(client, make_user):
    me = client.get("/auth/me", headers=login_headers(client, make_user("OPS"))).json()

    assert me["role"] == "OPERATIONAL_MANAGER"
    assert {"review:attendance", "view:audit"} <= set(me["permissions"])


def test_deactivated_account_is_rejected_immediately(client, make_user):
    user = make_user("ADMIN")
    headers = login_headers(client, user)

    user.query("UPDATE users SET is_active = false WHERE user_id = %s", (user.user_id,))
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
