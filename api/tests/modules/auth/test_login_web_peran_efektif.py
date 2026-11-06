"""Login web mengikuti peran efektif (ADR 0002 bagian Keputusan): peran utama + tambahan aktif memuat peran kantor
=> web diizinkan; hanya lapangan => ditolak. Flag mati = perilaku lama. Mobile tidak berubah."""
from __future__ import annotations

import pytest

from app.core.config import settings
from tests.conftest import requires_db, sync_query

pytestmark = requires_db


def _tambah(user, role: str) -> None:
    sync_query(
        "INSERT INTO user_role_assignment (user_id, role, office_id, source) VALUES (%s, %s, %s, 'MANUAL')",
        (user.user_id, role, user.org_id),
    )


def _login(client, user, platform: str):
    client.cookies.clear()
    return client.post(
        "/auth/login",
        json={"email": user.login, "password": user.password, "platform": platform},
        headers={"X-Device-Label": f"uji-{platform}"},
    )


@pytest.mark.parametrize(
    ("utama", "tambahan", "web", "mobile"),
    [
        ("EMPLOYEE", None, 403, 200),
        ("EMPLOYEE", "ADMIN_HR_GA", 200, 200),
        ("TEAM_LEADER", "OPERATIONAL_MANAGER", 200, 200),
        ("TEAM_LEADER", None, 403, 200),
        ("SUPER_ADMIN", None, 200, 200),
    ],
)
def test_matriks_flag_hidup(client, make_user, monkeypatch, utama, tambahan, web, mobile):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    user = make_user(utama)
    if tambahan:
        _tambah(user, tambahan)
    r = _login(client, user, "web")
    assert r.status_code == web, r.text
    if web == 403:
        assert "NOT_OFFICE_ACCOUNT" in r.text
    assert _login(client, user, "mobile").status_code == mobile


def test_web_peran_ganda_me_mengikuti_izin_efektif(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    user = make_user("EMPLOYEE")
    _tambah(user, "ADMIN_HR_GA")
    r = _login(client, user, "web")
    assert r.status_code == 200, r.text
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["role"] == "EMPLOYEE"
    hr = [s for s in body["role_scopes"] if s["role"] == "ADMIN_HR_GA"]
    assert len(hr) == 1
    assert hr[0]["office_id"] == str(user.org_id)


def test_peran_tambahan_dicabut_kembali_ditolak(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    user = make_user("EMPLOYEE")
    _tambah(user, "ADMIN_HR_GA")
    assert _login(client, user, "web").status_code == 200
    sync_query("UPDATE user_role_assignment SET delete_at = now() WHERE user_id = %s", (user.user_id,))
    assert _login(client, user, "web").status_code == 403


def test_flag_mati_tetap_ditolak(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)
    user = make_user("EMPLOYEE")
    _tambah(user, "ADMIN_HR_GA")
    r = _login(client, user, "web")
    assert r.status_code == 403
    assert "NOT_OFFICE_ACCOUNT" in r.text
