"""
V-12 · Absensi mengikuti `domain.js` CHECK_IN / CHECK_OUT / EXPLAIN_ATTENDANCE / REVIEW_ATTENDANCE.
Jarak, status, terlambat, dan pulang cepat diputuskan server (trigger `attendance_geofence`,
`attendance_checkout`, jam kerja organisasi — K-11); respons = yang tersimpan. Regresi R10:
jam perangkat tidak dipakai.
"""
from __future__ import annotations

import io
from datetime import timedelta

from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

INSIDE = {"lat": -6.2, "lng": 106.8}      # tepat di lokasi uji (radius 100 m)
OUTSIDE = {"lat": -6.3, "lng": 106.8}     # ±11 km


def _selfie(client, world: World, who: str) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (sum(map(ord, who)) % 255, 90, 30)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("swafoto.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def _check_in(client, world: World, who: str = "member", location=INSIDE, **extra):
    return client.post("/attendance/check-in", headers=world.headers(client, who),
                       json={"site_id": world.site_id, "location": location, **extra})


def _check_out(client, world: World, who: str = "member"):
    return client.post("/attendance/check-out", headers=world.headers(client, who), json={"location": INSIDE})


def _needs_review(client, world: World, who: str = "member") -> str:
    """Absensi di luar radius dengan swafoto → NEEDS_REVIEW (trigger)."""
    response = _check_in(client, world, who, OUTSIDE, selfie_file_id=_selfie(client, world, who))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "NEEDS_REVIEW"
    return response.json()["id"]


def _row(att_id: str) -> tuple:
    return sync_query("SELECT status::text, is_late, distance_m, check_out_at IS NOT NULL, is_early_leave, "
                      "explanation, review_note FROM vms.attendance WHERE id = %s", (att_id,))[0]


# ── CHECK_IN ──────────────────────────────────────────────────────────────────────────────────
def test_open_session_blocks_check_in_until_it_is_checked_out(client, world):
    """Sesi kemarin yang lupa ditutup: check-in ditolak, tetapi check-out tetap bisa menutupnya."""
    yesterday = jakarta_now().date() - timedelta(days=1)
    open_id = str(sync_query(
        "INSERT INTO vms.attendance (organization_id, employee_id, work_date, site_id, site_label, check_in_at, "
        "location, location_origin, radius_m) VALUES (%s, %s, %s, %s, 'Gudang uji', now() - interval '1 day', "
        "ST_GeogFromText('POINT(106.8 -6.2)'), 'GPS', 100) RETURNING id",
        (world.org_id, world.employees["member"], yesterday, world.site_id))[0][0])

    blocked = _check_in(client, world)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["message"] == "Masih ada sesi absensi terbuka."

    closed = _check_out(client, world)
    assert closed.status_code == 200, closed.text
    assert closed.json()["id"] == open_id and _row(open_id)[3] is True
    assert _check_in(client, world).status_code == 200


def test_one_attendance_per_day_unless_the_previous_one_was_rejected(client, world, fake_storage):
    att_id = _needs_review(client, world)
    assert _check_out(client, world).status_code == 200

    again = _check_in(client, world)
    assert again.status_code == 409, again.text
    assert again.json()["error"]["message"] == \
        "Absensi untuk hari ini sudah tercatat (hanya dapat mengajukan ulang jika absensi sebelumnya ditolak)."

    rejected = client.post(f"/attendance/{att_id}/review", headers=world.headers(client, "finance"),
                           json={"is_approved": False, "note": "Lokasi tidak sesuai penugasan"})
    assert rejected.status_code == 200, rejected.text
    assert _check_in(client, world).status_code == 200


def test_response_is_what_the_server_stored(client, world):
    """Sebelumnya respons memakai hitungan router (terlambat 09.00, SIMULASI → tinjau) yang berbeda
    dengan hasil trigger yang tersimpan."""
    response = _check_in(client, world, location_origin="SIMULASI")

    assert response.status_code == 200, response.text
    body = response.json()
    status, is_late, distance, *_ = _row(body["id"])
    assert (body["status"], body["is_late"], float(body["distance_m"])) == (status, is_late, float(distance))


def test_device_time_is_ignored(client, world):
    """R10 · jam perangkat tidak dipakai: waktu dari server, terlambat menurut jam kerja organisasi."""
    response = _check_in(client, world, check_in_at="2020-01-01T07:00:00+07:00", work_date="2020-01-01")

    assert response.status_code == 200, response.text
    assert sync_query(
        "SELECT abs(extract(epoch FROM a.check_in_at - now())) < 300, a.work_date = (now() AT TIME ZONE o.timezone)::date, "
        "a.is_late = ((a.check_in_at AT TIME ZONE o.timezone)::time > o.shift_start) "
        "FROM vms.attendance a JOIN vms.organization o ON o.id = a.organization_id WHERE a.id = %s",
        (response.json()["id"],)) == [(True, True, True)]


def test_outside_the_radius_needs_a_selfie(client, world):
    response = _check_in(client, world, location=OUTSIDE)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["message"].startswith("Di luar radius toleransi")
    assert sync_query("SELECT count(*) FROM vms.attendance WHERE employee_id = %s",
                      (world.employees["member"],)) == [(0,)]


# ── CHECK_OUT ─────────────────────────────────────────────────────────────────────────────────
def test_check_out_keeps_the_status_and_the_server_decides_early_leave(client, world):
    att_id = _check_in(client, world).json()["id"]

    response = _check_out(client, world)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "AUTO_VALID" == _row(att_id)[0]   # pulang cepat bukan alasan tinjau
    assert sync_query(
        "SELECT a.is_early_leave = ((a.check_out_at AT TIME ZONE o.timezone)::time < o.shift_end) "
        "FROM vms.attendance a JOIN vms.organization o ON o.id = a.organization_id WHERE a.id = %s",
        (att_id,)) == [(True,)]
    assert _check_out(client, world).status_code == 409                  # tidak ada sesi terbuka lagi


# ── EXPLAIN & REVIEW ──────────────────────────────────────────────────────────────────────────
def test_only_own_attendance_waiting_for_review_can_be_explained(client, world, fake_storage):
    valid_id = _check_in(client, world, who="leader").json()["id"]
    waiting_id = _needs_review(client, world)
    member = world.headers(client, "member")

    not_waiting = client.post(f"/attendance/{valid_id}/explain", headers=world.headers(client, "leader"),
                              json={"explanation": "Macet"})
    assert not_waiting.status_code == 409, not_waiting.text
    assert not_waiting.json()["error"]["message"] == \
        "Hanya absensi sendiri yang menunggu pemeriksaan dapat diberi penjelasan."
    assert client.post(f"/attendance/{waiting_id}/explain", headers=member,
                       json={"explanation": "   "}).status_code == 422
    assert client.post(f"/attendance/{waiting_id}/explain", headers=member,
                       json={"explanation": "Titik lokasi di gerbang proyek"}).status_code == 200
    assert _row(waiting_id)[5] == "Titik lokasi di gerbang proyek"


def test_review_rules(client, world, fake_storage):
    finance = world.headers(client, "finance")
    valid_id = _check_in(client, world, who="leader").json()["id"]
    own_id = _needs_review(client, world, who="finance")
    waiting_id = _needs_review(client, world)

    def review(att_id, **body):
        return client.post(f"/attendance/{att_id}/review", headers=finance, json={"is_approved": True, **body})

    assert review(valid_id, note="Oke").json()["error"]["message"] == "Absensi tidak menunggu pemeriksaan."
    own = review(own_id, note="Oke")
    assert own.status_code == 403 and own.json()["error"]["message"] == "Anda tidak boleh memverifikasi absensi sendiri."
    missing_note = review(waiting_id)
    assert missing_note.status_code == 422 and missing_note.json()["error"]["message"] == \
        "Catatan pemeriksaan wajib diisi."
    assert review(waiting_id, note="Lokasi sesuai surat tugas").status_code == 200
    assert _row(waiting_id)[0] == "APPROVED" and _row(waiting_id)[6] == "Lokasi sesuai surat tugas"
