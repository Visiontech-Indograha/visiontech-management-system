"""
Kredensial perangkat (masuk dengan sidik jari): terbit, pakai, rotasi, pemakaian ulang, kedaluwarsa, pencabutan
(logout, ganti sandi, nonaktif, keluarkan perangkat, peran dicabut), dan balapan dua pemakaian token yang sama.
"""
from __future__ import annotations

import hashlib

from tests.concurrency import dua_bersamaan
from tests.conftest import SeededUser, login_headers, requires_db, sync_query

pytestmark = requires_db

LABEL = {"X-Device-Label": "HP uji sidik jari"}


def _mobile_login(client, user: SeededUser, label: str = "HP uji sidik jari"):
    r = client.post(
        "/auth/login",
        json={"email": user.login, "password": user.password, "platform": "mobile"},
        headers={"X-Device-Label": label},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Device-Label": label}


def _issue(client, headers) -> str:
    r = client.post("/auth/device-credential", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["device_token"]


def _bio(client, token: str, label: str = "HP uji sidik jari"):
    return client.post("/auth/biometric-login", json={"device_token": token}, headers={"X-Device-Label": label})


def _rows(user_id: str):
    return sync_query(
        "SELECT revoked_at IS NOT NULL, revoked_reason, token_hash FROM device_credential "
        "WHERE user_id = %s ORDER BY create_at",
        (user_id,),
    )


def _aktif(user_id: str) -> int:
    return sync_query(
        "SELECT count(*) FROM device_credential WHERE user_id = %s AND revoked_at IS NULL", (user_id,)
    )[0][0]


def test_terbit_menyimpan_hash_bukan_token(client, make_user):
    user = make_user("EMPLOYEE")
    token = _issue(client, _mobile_login(client, user))
    rows = _rows(user.user_id)
    assert len(rows) == 1 and rows[0][2].strip() == hashlib.sha256(token.encode()).hexdigest()
    assert token not in str(sync_query("SELECT * FROM device_credential WHERE user_id = %s", (user.user_id,)))
    exp = sync_query(
        "SELECT expires_at - create_at FROM device_credential WHERE user_id = %s", (user.user_id,)
    )[0][0]
    assert 29 <= exp.days <= 30


def test_terbit_butuh_login(client):
    assert client.post("/auth/device-credential").status_code == 401


def test_token_valid_masuk_dan_dirotasi(client, make_user):
    user = make_user("EMPLOYEE")
    t1 = _issue(client, _mobile_login(client, user))
    r = _bio(client, t1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"] and body["device_token"] != t1 and body["device_token_expires_at"]
    assert "refresh_token=" in r.headers.get("set-cookie", "")
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert _aktif(user.user_id) == 1  # hanya token baru yang aktif
    assert _bio(client, body["device_token"]).status_code == 200  # token baru berlaku


def test_token_salah_ditolak_pesan_awam(client):
    r = _bio(client, "salah-" + "x" * 40)
    assert r.status_code == 401
    assert "sidik jari" in r.text and "kata sandi" in r.text


def test_token_terlalu_pendek_422(client):
    assert client.post("/auth/biometric-login", json={"device_token": "pendek"}).status_code == 422


def test_kedaluwarsa_ditolak(client, make_user):
    user = make_user("EMPLOYEE")
    token = _issue(client, _mobile_login(client, user))
    sync_query("UPDATE device_credential SET expires_at = now() - interval '1 minute' WHERE user_id = %s",
               (user.user_id,))
    assert _bio(client, token).status_code == 401


def test_pakai_ulang_token_lama_mencabut_kredensial_baru(client, make_user):
    user = make_user("EMPLOYEE")
    t1 = _issue(client, _mobile_login(client, user))
    t2 = _bio(client, t1).json()["device_token"]
    r = _bio(client, t1)  # token usang dipakai lagi: kemungkinan bocor
    assert r.status_code == 401 and r.json()["error"]["code"] == "BIOMETRIC_REUSED"
    assert _aktif(user.user_id) == 0
    assert _bio(client, t2).status_code == 401
    acts = [a[0] for a in sync_query(
        "SELECT action FROM app_activity_logs WHERE entity_table = 'device_credential' AND actor_user_id = %s",
        (user.user_id,))]
    assert {"DEVICE_CRED_ISSUED", "DEVICE_CRED_USED", "DEVICE_CRED_REUSE"} <= set(acts)


def test_terbit_ulang_mencabut_yang_lama(client, make_user):
    user = make_user("EMPLOYEE")
    h = _mobile_login(client, user)
    t1 = _issue(client, h)
    t2 = _issue(client, h)
    assert _aktif(user.user_id) == 1
    assert _bio(client, t1).status_code == 401
    assert _bio(client, t2).status_code == 200


def test_logout_mencabut(client, make_user):
    user = make_user("EMPLOYEE")
    t = _issue(client, _mobile_login(client, user))
    assert client.post("/auth/logout").status_code == 200
    assert _aktif(user.user_id) == 0
    assert _bio(client, t).status_code == 401


def test_ganti_sandi_mencabut(client, make_user):
    user = make_user("EMPLOYEE")
    h = _mobile_login(client, user)
    t = _issue(client, h)
    r = client.post("/auth/change-password", headers=h,
                    json={"current_password": user.password, "new_password": "KataSandiBaru-456!"})
    assert r.status_code == 200, r.text
    assert _bio(client, t).status_code == 401


def test_akun_nonaktif_ditolak_dan_dicabut(client, make_user):
    user = make_user("EMPLOYEE")
    t = _issue(client, _mobile_login(client, user))
    sync_query("UPDATE users SET is_active = FALSE WHERE user_id = %s", (user.user_id,))
    r = _bio(client, t)
    assert r.status_code == 403 and r.json()["error"]["code"] == "INACTIVE"
    assert _aktif(user.user_id) == 0


def test_keluarkan_perangkat_mencabut(client, make_user):
    user = make_user("EMPLOYEE")
    h1 = _mobile_login(client, user, "HP satu")
    t1 = _issue(client, h1)
    client.cookies.clear()
    h2 = _mobile_login(client, user, "HP dua")
    t2 = _issue(client, h2)
    sid = next(s["id"] for s in client.get("/auth/sessions", headers=h2).json() if s["device_label"] == "HP satu")
    assert client.post(f"/auth/sessions/{sid}/revoke", headers=h2).status_code == 200
    assert _bio(client, t1, "HP satu").status_code == 401
    assert _bio(client, t2, "HP dua").status_code == 200


def test_keluarkan_perangkat_lain_mencabut(client, make_user):
    user = make_user("EMPLOYEE")
    t1 = _issue(client, _mobile_login(client, user, "HP satu"))
    client.cookies.clear()
    h2 = _mobile_login(client, user, "HP dua")
    t2 = _issue(client, h2)
    assert client.post("/auth/sessions/revoke-others", headers=h2).status_code == 200
    assert _bio(client, t1, "HP satu").status_code == 401
    assert _bio(client, t2, "HP dua").status_code == 200


def test_peran_dicabut_admin_mencabut(client, make_user, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    admin = make_user("SUPER_ADMIN")
    user = make_user("EMPLOYEE")
    t = _issue(client, _mobile_login(client, user))
    sync_query(
        "INSERT INTO user_role_assignment (user_id, role, office_id, source) "
        "VALUES (%s, 'ADMIN_HR_GA', %s, 'MANUAL')", (user.user_id, user.org_id))
    aid = sync_query("SELECT assignment_id FROM user_role_assignment WHERE user_id = %s AND source = 'MANUAL'",
                     (user.user_id,))[0][0]
    client.cookies.clear()
    r = client.delete(f"/users/{user.user_id}/role-assignments/{aid}", headers=login_headers(client, admin))
    assert r.status_code == 204, r.text
    assert _bio(client, t).status_code == 401


def test_dua_pemakaian_serentak_hanya_satu_berhasil(client, make_user):
    user = make_user("EMPLOYEE")
    t = _issue(client, _mobile_login(client, user))
    hasil = dua_bersamaan(lambda i: _bio(client, t))
    assert sorted(r.status_code for r in hasil) == [200, 401], [r.text for r in hasil]
    assert _aktif(user.user_id) <= 1
