"""
R-19 · P1-7 / M1 — daftar sesi aktif + "keluarkan perangkat lain" (pencabutan sesi).
- GET /auth/sessions: sesi AKTIF milik sendiri (satu per perangkat), yang sedang dipakai ditandai.
- POST /auth/sessions/{id}/revoke: satu perangkat milik sendiri; sesi orang lain → 404.
- POST /auth/sessions/revoke-others: semua perangkat lain; perangkat ini tetap masuk.
Token akses berumur 15 menit tidak diperiksa ke tabel sesi — yang dicabut adalah refresh-nya.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import API_PREFIX, app
from tests.conftest import SeededUser, requires_db

pytestmark = requires_db


def _device(user: SeededUser, label: str) -> tuple[TestClient, dict[str, str]]:
    """Satu perangkat = satu TestClient (cookie refresh sendiri) + token aksesnya."""
    c = TestClient(app, base_url=f"https://testserver{API_PREFIX}", headers={"User-Agent": label})
    token = c.post("/auth/login", json={"email": user.login, "password": user.password}).json()["access_token"]
    return c, {"Authorization": f"Bearer {token}"}


def test_list_shows_own_active_devices_and_marks_the_current_one(seeded_user, make_user):
    laptop, laptop_auth = _device(seeded_user, "Laptop kantor")
    phone, _ = _device(seeded_user, "HP lapangan")
    _device(make_user("HR"), "Orang lain")

    listed = laptop.get("/auth/sessions", headers=laptop_auth)
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert len(rows) == 2                                            # hanya milik sendiri
    assert [r["current"] for r in rows].count(True) == 1
    current = next(r for r in rows if r["current"])
    assert current["user_agent"] == "Laptop kantor"
    assert {r["user_agent"] for r in rows} == {"Laptop kantor", "HP lapangan"}
    assert all(r["issued_at"] for r in rows)
    laptop.close()
    phone.close()


def test_revoke_others_keeps_this_device_and_blocks_their_refresh(seeded_user):
    laptop, laptop_auth = _device(seeded_user, "Laptop kantor")
    phone, _ = _device(seeded_user, "HP lapangan")

    revoked = laptop.post("/auth/sessions/revoke-others", headers=laptop_auth)
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["revoked"] == 1

    assert phone.post("/auth/refresh").status_code == 401           # perangkat lain harus masuk lagi
    assert laptop.post("/auth/refresh").status_code == 200          # perangkat ini tetap
    assert seeded_user.query(
        "SELECT count(*) FROM vms.user_session WHERE user_id = %s AND state = 'ACTIVE'", (seeded_user.user_id,)
    ) == [(1,)]
    laptop.close()
    phone.close()


def test_revoke_single_device_only_own(seeded_user, make_user):
    laptop, laptop_auth = _device(seeded_user, "Laptop kantor")
    phone, _ = _device(seeded_user, "HP lapangan")
    phone_id = next(r["id"] for r in laptop.get("/auth/sessions", headers=laptop_auth).json() if not r["current"])

    other, other_auth = _device(make_user("HR"), "Orang lain")
    assert other.post(f"/auth/sessions/{phone_id}/revoke", headers=other_auth).status_code == 404

    assert laptop.post(f"/auth/sessions/{phone_id}/revoke", headers=laptop_auth).status_code == 200
    assert phone.post("/auth/refresh").status_code == 401
    assert [r["user_agent"] for r in laptop.get("/auth/sessions", headers=laptop_auth).json()] == ["Laptop kantor"]
    for c in (laptop, phone, other):
        c.close()
