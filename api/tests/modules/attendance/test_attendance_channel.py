"""
Absensi dipisah per jenis pekerja (docs/35 §1, Master Schema V2): jenis pekerja mengikuti peran —
TEAM_LEADER/EMPLOYEE → aplikasi HP (`channel` MOBILE), peran kantor → web (`channel` WEB).
Kanal yang salah ditolak server; jenis pekerja dibaca dari basis data, bukan dari klien.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.conftest import WORLD_PASSWORD, World, isolate_site, requires_db, sync_query

pytestmark = requires_db

INSIDE = {"lat": -6.2, "lng": 106.8}      # tepat di kantor uji (radius 100 m)
NEAR = {"lat": -6.2018, "lng": 106.8}     # ±200 m — di luar radius 100 m


@pytest.fixture(autouse=True)
def _storage(fake_storage):
    return fake_storage


def _selfie(client, world: World, who: str) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (sum(map(ord, who)) % 255, 20, 30)).save(buf, "PNG")
    return client.post("/files/upload", headers=world.headers(client, who),
                       files={"file": ("s.png", buf.getvalue(), "image/png")}).json()["file_id"]


def _check_in(client, world: World, who: str, channel: str | None, location=INSIDE, site_id=None, **extra):
    extra.setdefault("explanation", "Rapat di luar kantor")  # R-33: wajib di luar zona
    extra.setdefault("selfie_file_id", _selfie(client, world, who))
    body = {"site_id": site_id or world.site_id, "location": location, **extra}
    if channel:
        body["channel"] = channel
    return client.post("/attendance/check-in", headers=world.headers(client, who), json=body)


def _check_out(client, world: World, who: str, channel: str):
    return client.post("/attendance/check-out", headers=world.headers(client, who),
                       json={"channel": channel, "location": INSIDE})


@pytest.fixture
def new_office():
    """Kantor tambahan untuk satu uji; dihapus beserta absensinya sesudahnya."""
    from tests.cleanup import purge_office
    from tests.conftest import _sync_conn

    made: list[str] = []

    def make(name: str, lat: float = -6.2, lng: float = 106.8) -> str:
        made.append(str(sync_query(
            "INSERT INTO office (name, address, latitude, longitude) "
            "VALUES (%s, 'Jl. Uji', %s, %s) RETURNING office_id", (name, lat, lng))[0][0]))
        return made[-1]

    yield make
    with _sync_conn() as conn:
        for office_id in made:
            purge_office(conn, office_id)


def test_field_worker_rejected_on_web_and_accepted_on_mobile(client, world):
    web = _check_in(client, world, "member", "WEB")
    assert web.status_code == 403, web.text
    assert web.json()["error"]["code"] == "WRONG_ATTENDANCE_CHANNEL"
    assert "aplikasi HP" in web.json()["error"]["message"]

    # Klien lama tanpa `channel` dianggap MOBILE dan tetap diterima.
    mobile = _check_in(client, world, "member", None)
    assert mobile.status_code == 200, mobile.text
    assert mobile.json()["status"] == "AUTO_VALID"


def test_office_worker_rejected_on_mobile_and_checks_in_out_on_web(client, world):
    mobile = _check_in(client, world, "pm", "MOBILE")
    assert mobile.status_code == 403, mobile.text
    assert mobile.json()["error"]["code"] == "WRONG_ATTENDANCE_CHANNEL"
    assert "lewat web" in mobile.json()["error"]["message"]

    web = _check_in(client, world, "pm", "WEB", accuracy_m=40)
    assert web.status_code == 200, web.text
    att_id = web.json()["id"]
    assert web.json()["status"] == "AUTO_VALID"

    # Pulang juga lewat kanal yang sesuai; dari HP ditolak, sesi tetap terbuka.
    assert _check_out(client, world, "pm", "MOBILE").status_code == 403
    out = _check_out(client, world, "pm", "WEB")
    assert out.status_code == 200, out.text
    # Tulis → baca ulang
    listed = client.get("/attendance", headers=world.headers(client, "pm"),
                        params={"employee_id": world.employees["pm"]}).json()["items"]
    assert [a["id"] for a in listed if a["check_out_at"]] == [att_id]


def test_web_out_of_radius_needs_an_explanation_then_review(client, world):
    center = isolate_site(world)  # kantor lain (radius besar) tak boleh menampung titik ini
    near = {"lat": center["lat"] - 0.0018, "lng": center["lng"]}  # ±200 m
    without = _check_in(client, world, "pm", "WEB", location=near, accuracy_m=80, explanation=None)
    assert without.status_code == 422 and without.json()["error"]["code"] == "EXPLANATION_REQUIRED"

    response = _check_in(client, world, "pm", "WEB", location=near, accuracy_m=80)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "NEEDS_REVIEW"
    assert response.json()["distance_m"] > 100


def test_web_accuracy_limit_is_looser_than_mobile(client, world):
    """Lokasi browser laptop dari WiFi: batas 300 m (HP tetap 100 m, K-12)."""
    assert _check_in(client, world, "pm", "WEB", accuracy_m=301).status_code == 422
    assert _check_in(client, world, "pm", "WEB", accuracy_m=250).status_code == 200


def test_me_exposes_attendance_mode_from_the_role(client, world):
    assert client.get("/auth/me", headers=world.headers(client, "member")).json()["attendance_mode"] == "FIELD"
    assert client.get("/auth/me", headers=world.headers(client, "leader")).json()["attendance_mode"] == "FIELD"
    assert client.get("/auth/me", headers=world.headers(client, "pm")).json()["attendance_mode"] == "OFFICE"


def test_login_platform_follows_the_role(client, world):
    """docs/35 §1: peran lapangan masuk lewat HP, peran kantor lewat web (docs/41 §2: SUPER_ADMIN boleh keduanya)."""
    for who, allowed in (("member", "mobile"), ("leader", "mobile"), ("pm", "web"), ("hr", "web")):
        creds = {"email": world.logins[who], "password": WORLD_PASSWORD}
        denied = "web" if allowed == "mobile" else "mobile"
        assert client.post("/auth/login", json={**creds, "platform": denied}).status_code == 403, who
        assert client.post("/auth/login", json={**creds, "platform": allowed}).status_code == 200, who


def test_super_admin_logs_in_on_both_platforms(client, world):
    creds = {"email": world.logins["admin"], "password": WORLD_PASSWORD}
    for platform in ("web", "mobile"):
        assert client.post("/auth/login", json={**creds, "platform": platform}).status_code == 200, platform


def test_field_worker_can_check_in_at_any_office(client, world, new_office):
    """Kantor Visiontech ada beberapa: semuanya tampil di daftar absen dan pekerja memilih sendiri."""
    offices = [new_office("Kantor A uji"), new_office("Kantor B uji", 0.5, 101.4)]
    listed = {s["id"] for s in client.get("/offices", headers=world.headers(client, "member"),
                                          params={"for_attendance": "true"}).json()}
    assert set(offices) <= listed
    # APK lama memanggil /offices tanpa for_attendance — kantor juga harus ada.
    assert set(offices) <= {s["id"] for s in client.get("/offices", headers=world.headers(client, "member")).json()}

    res = _check_in(client, world, "member", "MOBILE", site_id=offices[1], location={"lat": 0.5, "lng": 101.4})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "AUTO_VALID"
    stored = sync_query("SELECT office_id::text FROM attendance WHERE attendance_id = %s", (res.json()["id"],))
    assert stored[0][0] == offices[1]
