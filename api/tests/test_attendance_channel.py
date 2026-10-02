"""
Absensi dipisah per jenis pekerja (docs/10 Bagian C, 2026-10-01): `employee.attendance_mode`
FIELD → absen lewat aplikasi HP (`channel` MOBILE), OFFICE → absen lewat web (`channel` WEB).
Kanal yang salah ditolak server; jenis pekerja dibaca dari basis data, bukan dari klien.
"""
from __future__ import annotations

import io

from PIL import Image

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

INSIDE = {"lat": -6.2, "lng": 106.8}      # tepat di lokasi uji (radius 100 m)
NEAR = {"lat": -6.2018, "lng": 106.8}     # ±200 m — di luar radius 100 m


def _set_mode(world: World, who: str, mode: str) -> str | None:
    """Ubah jenis pekerja; untuk OFFICE kembalikan lokasi kantor (tanpa unit) — R-33: pekerja kantor
    hanya absen di lokasi kantor."""
    sync_query("UPDATE vms.employee SET attendance_mode = %s WHERE id = %s RETURNING id",
               (mode, world.employees[who]))
    if mode != "OFFICE":
        return None
    return str(sync_query(
        "INSERT INTO vms.site (organization_id, name, location, radius_m) "
        "VALUES (%s, 'Kantor uji', ST_GeogFromText('POINT(106.8 -6.2)'), 100) RETURNING id", (world.org_id,))[0][0])


def _check_in(client, world: World, who: str, channel: str | None, location=INSIDE, site_id=None, **extra):
    extra.setdefault("explanation", "Rapat di luar kantor")  # R-33: wajib di luar zona
    body = {"site_id": site_id or world.site_id, "location": location, **extra}
    if channel:
        body["channel"] = channel
    return client.post("/attendance/check-in", headers=world.headers(client, who), json=body)


def _check_out(client, world: World, who: str, channel: str):
    return client.post("/attendance/check-out", headers=world.headers(client, who),
                       json={"channel": channel, "location": INSIDE})


def test_field_worker_rejected_on_web_and_accepted_on_mobile(client, world):
    web = _check_in(client, world, "member", "WEB")
    assert web.status_code == 403, web.text
    assert web.json()["error"]["code"] == "WRONG_ATTENDANCE_CHANNEL"
    assert "aplikasi HP" in web.json()["error"]["message"]

    # Klien lama tanpa `channel` dianggap MOBILE dan tetap diterima.
    mobile = _check_in(client, world, "member", None)
    assert mobile.status_code == 200, mobile.text
    source = sync_query("SELECT source::text FROM vms.attendance WHERE id = %s", (mobile.json()["id"],))[0][0]
    assert source == "MOBILE"


def test_office_worker_rejected_on_mobile_and_checks_in_out_on_web(client, world):
    office = _set_mode(world, "member", "OFFICE")
    mobile = _check_in(client, world, "member", "MOBILE", site_id=office)
    assert mobile.status_code == 403, mobile.text
    assert mobile.json()["error"]["code"] == "WRONG_ATTENDANCE_CHANNEL"
    assert "lewat web" in mobile.json()["error"]["message"]

    web = _check_in(client, world, "member", "WEB", site_id=office, accuracy_m=40)
    assert web.status_code == 200, web.text
    att_id = web.json()["id"]
    assert web.json()["status"] == "AUTO_VALID"
    assert sync_query("SELECT source::text FROM vms.attendance WHERE id = %s", (att_id,))[0][0] == "WEB"

    # Pulang juga lewat kanal yang sesuai; dari HP ditolak, sesi tetap terbuka.
    assert _check_out(client, world, "member", "MOBILE").status_code == 403
    out = _check_out(client, world, "member", "WEB")
    assert out.status_code == 200, out.text
    # Tulis → baca ulang
    listed = client.get("/attendance", headers=world.headers(client, "member"),
                        params={"employee_id": world.employees["member"]}).json()["items"]
    assert [a["id"] for a in listed if a["check_out_at"]] == [att_id]


def test_web_out_of_radius_needs_a_selfie_then_review(client, world, fake_storage):
    """R-33: absen web di luar radius juga wajib swafoto; dengan swafoto → NEEDS_REVIEW."""
    office = _set_mode(world, "member", "OFFICE")
    without = _check_in(client, world, "member", "WEB", site_id=office, location=NEAR, accuracy_m=80)
    assert without.status_code == 422 and "swafoto wajib" in without.json()["error"]["message"]
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (10, 20, 30)).save(buf, "PNG")
    selfie = client.post("/files/upload", headers=world.headers(client, "member"),
                         files={"file": ("s.png", buf.getvalue(), "image/png")}).json()["file_id"]
    response = _check_in(client, world, "member", "WEB", site_id=office, location=NEAR, accuracy_m=80,
                         selfie_file_id=selfie)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "NEEDS_REVIEW"
    assert response.json()["distance_m"] > 100


def test_web_accuracy_limit_is_looser_than_mobile(client, world):
    """Lokasi browser laptop dari WiFi: batas 300 m (HP tetap 100 m, K-12)."""
    office = _set_mode(world, "member", "OFFICE")
    assert _check_in(client, world, "member", "WEB", site_id=office, accuracy_m=301).status_code == 422
    assert _check_in(client, world, "member", "WEB", site_id=office, accuracy_m=250).status_code == 200


def test_me_and_employee_expose_attendance_mode_and_hr_can_change_it(client, world):
    me = client.get("/auth/me", headers=world.headers(client, "member")).json()
    assert me["attendance_mode"] == "FIELD"

    emp_id = world.employees["member"]
    updated = client.put(f"/employees/{emp_id}", headers=world.headers(client, "hr"),
                         json={"attendance_mode": "OFFICE"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["attendance_mode"] == "OFFICE"
    # Tulis → baca ulang
    assert client.get(f"/employees/{emp_id}", headers=world.headers(client, "hr")).json()["attendance_mode"] == "OFFICE"
    assert client.get("/auth/me", headers=world.headers(client, "member")).json()["attendance_mode"] == "OFFICE"

    # Nilai tak dikenal ditolak skema; null berarti tidak diubah.
    assert client.put(f"/employees/{emp_id}", headers=world.headers(client, "hr"),
                      json={"attendance_mode": "REMOTE"}).status_code == 422
    kept = client.put(f"/employees/{emp_id}", headers=world.headers(client, "hr"),
                      json={"attendance_mode": None, "phone": "0812"})
    assert kept.status_code == 200, kept.text
    assert kept.json()["attendance_mode"] == "OFFICE"
