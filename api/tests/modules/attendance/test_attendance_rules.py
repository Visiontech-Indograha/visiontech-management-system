"""
V-12 · Aturan absen masuk / pulang / penjelasan / pemeriksaan (Master Schema V2, docs/35 §5).
Jarak, status, terlambat, dan pulang cepat diputuskan server; respons = yang tersimpan. Regresi R10:
jam perangkat tidak dipakai. Swafoto selalu wajib; anggota & ketua tim absen lewat HP, peran kantor lewat web.
"""
from __future__ import annotations

import io
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import World, isolate_site, requires_db, sync_query

WIB = ZoneInfo("Asia/Jakarta")

pytestmark = requires_db

INSIDE = {"lat": -6.2, "lng": 106.8}      # tepat di kantor uji (radius 100 m)
OUTSIDE = {"lat": -6.3, "lng": 106.8}     # ±11 km
FIELD = ("member", "leader")              # peran lapangan → kanal HP


@pytest.fixture(autouse=True)
def _storage(fake_storage):
    """Swafoto selalu diunggah — penyimpanan palsu untuk semua uji di modul ini."""
    return fake_storage


def _channel(who: str) -> str:
    return "MOBILE" if who in FIELD else "WEB"


def _selfie(client, world: World, who: str) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (sum(map(ord, who)) % 255, 90, 30)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("swafoto.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def _check_in(client, world: World, who: str = "member", location=INSIDE, **extra):
    # R-33: penjelasan wajib di luar zona & saat mengajukan ulang — uji di sini menyertakannya kecuali diminta lain.
    extra.setdefault("explanation", "Survei titik di luar lokasi")
    extra.setdefault("selfie_file_id", _selfie(client, world, who))
    return client.post("/attendance/check-in", headers=world.headers(client, who),
                       json={"site_id": world.site_id, "location": location, "channel": _channel(who), **extra})


def _check_out(client, world: World, who: str = "member"):
    # Swafoto ikut dikirim seperti aplikasi HP: absen pulang juga diperiksa wajahnya (F8).
    return client.post("/attendance/check-out", headers=world.headers(client, who),
                       json={"location": INSIDE, "channel": _channel(who),
                             "selfie_file_id": _selfie(client, world, who)})


def _needs_review(client, world: World, who: str = "member") -> str:
    """Absen di luar radius dengan swafoto + penjelasan → menunggu pemeriksaan."""
    response = _check_in(client, world, who, OUTSIDE)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "NEEDS_REVIEW"
    return response.json()["id"]


_STATUS = ("CASE om_approval_status WHEN 'AUTO_VALID' THEN 'AUTO_VALID' WHEN 'APPROVED_BY_OM' THEN 'APPROVED' "
           "WHEN 'REJECTED_BY_OM' THEN 'REJECTED' ELSE 'NEEDS_REVIEW' END")


def _row(att_id: str) -> tuple:
    return sync_query(
        f"SELECT {_STATUS}, (clock_in_at AT TIME ZONE 'Asia/Jakarta')::time > TIME '08:00', distance_to_target_m, clock_out_at IS NOT NULL, "
        "(clock_out_at IS NOT NULL AND (clock_out_at AT TIME ZONE 'Asia/Jakarta')::time < scheduled_out), out_of_radius_note "
        "FROM attendance WHERE attendance_id = %s", (att_id,))[0]


def _count(world: World, who: str = "member") -> int:
    return sync_query("SELECT count(*) FROM attendance WHERE employee_id = %s", (world.employees[who],))[0][0]


# ── CHECK_IN ──────────────────────────────────────────────────────────────────────────────────
def _open_stale(world, who: str, clock_in_hm: str) -> str:
    """Sisipkan sesi tanggal kemarin (WIB) yang belum ditutup, masuk pukul `clock_in_hm`; kembalikan id-nya."""
    yesterday = jakarta_now().date() - timedelta(days=1)
    clock_in = datetime.combine(yesterday, time.fromisoformat(clock_in_hm), tzinfo=WIB)
    return str(sync_query(
        "INSERT INTO attendance (employee_id, attendance_date, target_location_type, office_id, scheduled_in, "
        "scheduled_out, clock_in_at, in_lat, in_lng, face_match_score, face_photo_path, distance_to_target_m, "
        "is_within_attendance_radius, distance_from_main_office_m, city_zone_status, meal_allowance_amount) "
        "VALUES (%s, %s, 'OFFICE', %s, '07:00', '16:00', %s, -6.2, 106.8, 0, 'uji.webp', "
        "0, TRUE, 0, 'DALAM_KOTA', 0) RETURNING attendance_id",
        (world.employees[who], yesterday, world.site_id, clock_in))[0][0])


def test_stale_session_is_closed_on_next_day_check_in(client, world):
    """Sesi kemarin yang lupa absen pulang tidak mengunci absen masuk hari ini: ditutup otomatis (19:00 kemarin)."""
    open_id = _open_stale(world, "member", "08:00")
    assert _row(open_id)[3] is False

    # Pulang online untuk sesi lintas hari ditolak: sesi itu sudah berakhir pada tengah malam.
    refused = _check_out(client, world)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "NO_OPEN_SESSION"

    checked_in = _check_in(client, world)
    assert checked_in.status_code == 200, checked_in.text
    assert _row(open_id)[3] is True
    assert "Lupa absen pulang" in _row(open_id)[5]
    closed_at = sync_query(
        "SELECT (clock_out_at AT TIME ZONE 'Asia/Jakarta')::text FROM attendance WHERE attendance_id = %s", (open_id,))
    assert closed_at[0][0].startswith(str(jakarta_now().date() - timedelta(days=1)) + " 19:00")


def test_night_shift_session_ends_at_midnight_when_checking_in_next_day(client, world):
    """Kerja malam (masuk 22:04 kemarin): sesi berakhir 00:00 WIB hari ini, bukan 19:00 kemarin (sebelum masuk)."""
    open_id = _open_stale(world, "member", "22:04")
    assert _check_in(client, world).status_code == 200
    closed_at = sync_query(
        "SELECT (clock_out_at AT TIME ZONE 'Asia/Jakarta')::text FROM attendance WHERE attendance_id = %s", (open_id,))
    assert closed_at[0][0].startswith(str(jakarta_now().date()) + " 00:00")


def test_stale_session_does_not_show_a_checkout_reminder(client, world):
    """Pengingat pulang (required_out_at) hanya untuk sesi hari ini; sesi kemarin tidak menjadi 'Absen pulang'."""
    _open_stale(world, "member", "08:00")
    response = client.get("/attendance", headers=world.headers(client, "member"))
    assert response.status_code == 200, response.text
    assert response.json()["required_out_at"] is None



def test_one_attendance_per_day_unless_the_previous_one_was_rejected(client, world):
    att_id = _needs_review(client, world)
    # R-33: absen pulang hanya setelah absen masuk valid.
    pending_out = _check_out(client, world)
    assert pending_out.status_code == 409 and pending_out.json()["error"]["code"] == "CHECKOUT_NOT_VALID"

    again = _check_in(client, world)
    assert again.status_code == 409, again.text
    assert again.json()["error"]["code"] == "ALREADY_CHECKED_IN"

    rejected = client.post(f"/attendance/{att_id}/review", headers=world.headers(client, "pm"),
                           json={"is_approved": False, "note": "Lokasi tidak sesuai penugasan"})
    assert rejected.status_code == 200, rejected.text
    assert _check_in(client, world).status_code == 200


def test_response_is_what_the_server_stored(client, world):
    response = _check_in(client, world, location_origin="SIMULASI")

    assert response.status_code == 200, response.text
    body = response.json()
    status, is_late, distance, *_ = _row(body["id"])
    assert (body["status"], body["is_late"], float(body["distance_m"])) == (status, is_late, float(distance))


def test_device_time_is_ignored(client, world):
    """R10 · jam perangkat tidak dipakai: jam & tanggal dari server (WIB)."""
    response = _check_in(client, world, check_in_at="2020-01-01T07:00:00+07:00", work_date="2020-01-01")

    assert response.status_code == 200, response.text
    assert sync_query(
        "SELECT abs(extract(epoch FROM clock_in_at - now())) < 300, attendance_date = %s "
        "FROM attendance WHERE attendance_id = %s",
        (jakarta_now().date(), response.json()["id"])) == [(True, True)]


def test_outside_the_radius_needs_an_explanation(client, world):
    response = _check_in(client, world, location=OUTSIDE, explanation=None)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "EXPLANATION_REQUIRED"
    assert _count(world) == 0


def test_every_check_in_needs_a_selfie(client, world):
    response = _check_in(client, world, selfie_file_id=None)

    assert response.status_code == 422, response.text
    assert "swafoto" in response.json()["error"]["message"].lower()
    assert _count(world) == 0


# ── CHECK_OUT ─────────────────────────────────────────────────────────────────────────────────
def test_check_out_keeps_the_status_and_the_server_decides_early_leave(client, world):
    att_id = _check_in(client, world).json()["id"]

    response = _check_out(client, world)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "AUTO_VALID" == _row(att_id)[0]   # pulang cepat bukan alasan tinjau
    assert response.json()["is_early_leave"] == _row(att_id)[4]
    assert _check_out(client, world).status_code == 409                  # tidak ada sesi terbuka lagi


# ── EXPLAIN & REVIEW ──────────────────────────────────────────────────────────────────────────
def test_only_own_attendance_waiting_for_review_can_be_explained(client, world):
    valid_id = _check_in(client, world, who="leader").json()["id"]
    waiting_id = _needs_review(client, world)
    member = world.headers(client, "member")

    not_waiting = client.post(f"/attendance/{valid_id}/explain", headers=world.headers(client, "leader"),
                              json={"explanation": "Macet"})
    assert not_waiting.status_code == 409, not_waiting.text
    assert client.post(f"/attendance/{waiting_id}/explain", headers=member,
                       json={"explanation": "   "}).status_code == 422
    assert client.post(f"/attendance/{waiting_id}/explain", headers=member,
                       json={"explanation": "Titik lokasi di gerbang proyek"}).status_code == 200
    assert _row(waiting_id)[5] == "Titik lokasi di gerbang proyek"


def test_evidence_photo_is_attached_only_by_the_owner(client, world):
    """Foto bukti biasa: milik sendiri OK (tanpa wajah); absensi/foto orang lain ditolak."""
    att_id = _check_in(client, world, who="member").json()["id"]
    member, leader = world.headers(client, "member"), world.headers(client, "leader")
    own_photo, other_photo = _selfie(client, world, "member"), _selfie(client, world, "leader")

    assert client.post(f"/attendance/{att_id}/evidence", headers=leader,
                       json={"evidence_file_id": own_photo}).status_code == 404
    foreign = client.post(f"/attendance/{att_id}/evidence", headers=member, json={"evidence_file_id": other_photo})
    assert foreign.status_code == 422 and foreign.json()["error"]["code"] == "EVIDENCE_NOT_OWNED"
    ok = client.post(f"/attendance/{att_id}/evidence", headers=member, json={"evidence_file_id": own_photo})
    assert ok.status_code == 200, ok.text
    listed = client.get("/attendance", headers=member).json()["items"]
    assert [r["evidence_photo_file_id"] for r in listed if r["id"] == att_id] == [own_photo]


def test_review_rules(client, world):
    """Peninjau (PM/OM/HR/admin) tidak pernah memverifikasi absensi sendiri; catatan wajib."""
    pm = world.headers(client, "pm")
    valid_id = _check_in(client, world, who="leader").json()["id"]
    own_id = _needs_review(client, world, who="pm")
    waiting_id = _needs_review(client, world)

    def review(att_id, **body):
        return client.post(f"/attendance/{att_id}/review", headers=pm, json={"is_approved": True, **body})

    assert review(valid_id, note="Oke").json()["error"]["message"] == "Absensi tidak menunggu pemeriksaan."
    own = review(own_id, note="Oke")
    assert own.status_code == 403 and own.json()["error"]["message"] == "Anda tidak boleh memverifikasi absensi sendiri."
    missing_note = review(waiting_id)
    assert missing_note.status_code == 422 and missing_note.json()["error"]["message"] == \
        "Catatan pemeriksaan wajib diisi."
    assert review(waiting_id, note="Lokasi sesuai surat tugas").status_code == 200
    status, *_, note = _row(waiting_id)
    assert status == "APPROVED" and "Lokasi sesuai surat tugas" in note


def test_field_staff_cannot_review(client, world):
    waiting_id = _needs_review(client, world)
    body = {"is_approved": False, "note": "Tidak ada surat tugas di lokasi itu"}

    assert client.post(f"/attendance/{waiting_id}/review", headers=world.headers(client, "leader"),
                       json=body).status_code == 403
    assert client.post(f"/attendance/{waiting_id}/review", headers=world.headers(client, "pm"),
                       json=body).status_code == 200
    assert _row(waiting_id)[0] == "REJECTED"


# ── K-12 · akurasi GPS & batas radius (dok 07 §4.3) ──────────────────────────────────────────
def test_poor_gps_accuracy_is_rejected_with_a_reason(client, world):
    """K-12: akurasi GPS > 100 m ditolak dengan alasan dan tidak ada baris absensi yang tersimpan."""
    response = _check_in(client, world, accuracy_m=150.0)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "GPS_INACCURATE"
    assert "akurasi" in response.json()["error"]["message"].lower()
    assert _count(world) == 0


def test_gps_accuracy_at_the_limit_or_unknown_is_accepted(client, world):
    """Tepat 100 m masih diterima; klien lama / antrean offline tanpa `accuracy_m` tidak ditolak."""
    at_limit = _check_in(client, world, accuracy_m=100.0)
    assert at_limit.status_code == 200, at_limit.text
    assert _check_out(client, world).status_code == 200
    unknown = _check_in(client, world, "leader")
    assert unknown.status_code == 200, unknown.text


def test_radius_boundary_is_decided_consistently(client, world):
    """Tepat di tepi radius: titik ±99 m di dalam, ±101 m di luar — keputusan server stabil."""
    # Isolasi dari data global: semua kantor uji berpusat di (-6.2, 106.8), jadi kantor sisa/paralel berradius
    # lebih besar bisa "menang" di nearest_valid_site. Kantor uji ini dipindah ke koordinat unik yang tak dipakai
    # kantor lain, lalu titik dalam/luar dihitung dari pusat itu.
    center = isolate_site(world)
    radius = sync_query("SELECT attendance_radius_m FROM office WHERE office_id = %s", (world.site_id,))[0][0]
    deg_per_m = 1 / 111_320  # derajat lintang per meter
    inside = {"lat": center["lat"] + (radius - 1) * deg_per_m, "lng": center["lng"]}
    outside = {"lat": center["lat"] - (radius + 1) * deg_per_m, "lng": center["lng"]}

    near = _check_in(client, world, location=inside)
    assert near.status_code == 200, near.text
    assert near.json()["status"] == "AUTO_VALID" and near.json()["distance_m"] <= radius

    far = _check_in(client, world, "leader", outside, explanation=None)
    assert far.status_code == 422, far.text  # di luar radius tanpa penjelasan → ditolak
