"""
T-17 · Cookie refresh web sesuai dok 02 A-11 / dok 08 §3:
`HttpOnly; Secure; SameSite=Strict`, path terbatas `/api/v1/auth`. Logout menghapus cookie dengan
path yang sama (path berbeda = cookie lama tidak pernah terhapus di browser).
"""
from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db


def _set_cookie(response) -> str:
    header = response.headers.get("set-cookie", "")
    assert header.startswith("refresh_token="), header
    return header.lower()


def test_login_cookie_attributes(client, seeded_user):
    response = client.post("/auth/login", json={"email": seeded_user.login, "password": seeded_user.password})
    cookie = _set_cookie(response)

    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api/v1/auth" in cookie


def test_refresh_cookie_attributes(client, seeded_user):
    client.post("/auth/login", json={"email": seeded_user.login, "password": seeded_user.password})
    cookie = _set_cookie(client.post("/auth/refresh"))

    assert "samesite=strict" in cookie and "path=/api/v1/auth" in cookie


def test_logout_clears_cookie_on_same_path(client, seeded_user):
    client.post("/auth/login", json={"email": seeded_user.login, "password": seeded_user.password})
    cookie = _set_cookie(client.post("/auth/logout"))

    assert "path=/api/v1/auth" in cookie
    assert "max-age=0" in cookie or "expires=thu, 01 jan 1970" in cookie
