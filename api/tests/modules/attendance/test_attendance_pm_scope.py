"""
A1 · Akses absensi lintas divisi. PM hanya melihat & meninjau absensi karyawan divisi yang ia pimpin
(division.pm_id); OM/SUPER_ADMIN/pemegang VIEW_ALL tetap melihat semua. Swafoto mengikuti aturan yang sama
(`/files/{id}/url` → 404 untuk PM divisi lain).
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.conftest import World, requires_db, sync_query

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _second_division_pm(world: World) -> str:
    """PM kedua yang memimpin divisi lain di kantor yang sama (tanpa karyawan di divisi itu)."""
    unit2 = world.add_unit("Dua")
    pm2 = world.add_person("pm2", "PM", unit_id=unit2)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (pm2, unit2))
    return pm2


def _member_check_in(client, world: World) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (7, 77, 177)).save(buf, "PNG")
    selfie = client.post("/files/upload", headers=world.headers(client, "member"),
                         files={"file": ("swafoto.png", buf.getvalue(), "image/png")})
    assert selfie.status_code == 200, selfie.text
    # Di luar radius + penjelasan → status NEEDS_REVIEW (menunggu pemeriksaan PM divisinya).
    body = {"site_id": world.site_id, "location": {"lat": -6.3, "lng": 106.8}, "channel": "MOBILE",
            "selfie_file_id": selfie.json()["file_id"], "explanation": "Survei titik di luar lokasi"}
    check_in = client.post("/attendance/check-in", headers=world.headers(client, "member"), json=body)
    assert check_in.status_code == 200, check_in.text
    return check_in.json()["id"]


def _listed_ids(client, world: World, who: str) -> set[str]:
    response = client.get("/attendance", headers=world.headers(client, who))
    assert response.status_code == 200, response.text
    return {row["id"] for row in response.json()["items"]}


def test_pm_of_other_division_does_not_see_attendance_but_division_pm_does(client, world: World):
    att_id = _member_check_in(client, world)
    pm2 = _second_division_pm(world)
    assert pm2  # PM divisi lain sudah login sebagai "pm2"

    assert att_id in _listed_ids(client, world, "pm")
    assert att_id not in _listed_ids(client, world, "pm2")


def test_om_and_admin_still_see_every_division(client, world: World):
    att_id = _member_check_in(client, world)
    _second_division_pm(world)

    assert att_id in _listed_ids(client, world, "ops")
    assert att_id in _listed_ids(client, world, "admin")


def test_pm_of_other_division_cannot_review_attendance(client, world: World):
    att_id = _member_check_in(client, world)
    _second_division_pm(world)

    denied = client.post(f"/attendance/{att_id}/review", headers=world.headers(client, "pm2"),
                         json={"is_approved": True})
    assert denied.status_code in (403, 404), denied.text
    allowed = client.post(f"/attendance/{att_id}/review", headers=world.headers(client, "pm"),
                          json={"is_approved": True, "note": "Diperiksa PM divisi"})
    assert allowed.status_code == 200, allowed.text


def test_selfie_of_other_division_is_hidden_from_pm(client, world: World):
    att_id = _member_check_in(client, world)
    _second_division_pm(world)
    file_id = sync_query(
        "SELECT f.id::text FROM attendance a JOIN file_object f ON f.storage_key = a.face_photo_path "
        "WHERE a.attendance_id = %s", (att_id,))[0][0]

    assert client.get(f"/files/{file_id}/url", headers=world.headers(client, "pm")).status_code == 200
    assert client.get(f"/files/{file_id}/url", headers=world.headers(client, "pm2")).status_code == 404
    assert client.get(f"/files/{file_id}/url", headers=world.headers(client, "ops")).status_code == 200


def test_hr_sees_and_opens_selfies_of_every_division(client, world: World):
    """Keputusan pemilik HR: ADMIN_HR_GA melihat absensi & swafoto seluruh karyawan (sama seperti OM/Finance)."""
    att_id = _member_check_in(client, world)
    _second_division_pm(world)
    file_id = sync_query(
        "SELECT f.id::text FROM attendance a JOIN file_object f ON f.storage_key = a.face_photo_path "
        "WHERE a.attendance_id = %s", (att_id,))[0][0]

    assert att_id in _listed_ids(client, world, "hr")
    assert client.get(f"/files/{file_id}/url", headers=world.headers(client, "hr")).status_code == 200
