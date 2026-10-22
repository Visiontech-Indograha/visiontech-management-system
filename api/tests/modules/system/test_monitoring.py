"""
V-30 · Lini masa OPS dikelompokkan per pekerjaan + rekap absensi (dok 03 M11, dok 05 §3.13).
- GET /timeline?from=&to= — izin `view:timeline` (PM, OPS, ADMIN). Satu kelompok per SK yang terlihat,
  kecuali CANCELLED/COMPLETED (prototipe operations.js timeline()), urut tanggal mulai. Tiap hari berstatus
  APPROVED | SUBMITTED | CHANGES_REQUESTED | LATE | TODAY | UPCOMING; ringkasan approved_days & late_days.
- GET /recaps/attendance?month=YYYY-MM — HR/OPS/ADMIN: seluruh perusahaan; lainnya: hanya dirinya.
"""
from __future__ import annotations

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _timeline(client, world: World, who: str, **params):
    return client.get("/timeline", headers=world.headers(client, who), params=params)


def _group(body: list[dict], plan_id: str) -> dict | None:
    return next((g for g in body if g["id"] == plan_id), None)


def _attendance(world: World, who: str, om_status: str) -> None:
    sync_query(
        "INSERT INTO attendance (employee_id, attendance_date, target_location_type, office_id, scheduled_in, "
        "scheduled_out, clock_in_at, in_lat, in_lng, face_match_score, face_photo_path, distance_to_target_m, "
        "is_within_attendance_radius, om_approval_status, distance_from_main_office_m, city_zone_status, "
        "meal_allowance_amount) VALUES (%s, %s, 'OFFICE', %s, '07:00', '16:00', now(), -6.2, 106.8, 0, 'uji.webp', "
        "0, TRUE, %s, 0, 'DALAM_KOTA', 0) RETURNING 1",
        (world.employees[who], jakarta_now().date(), world.org_id, om_status))


def test_attendance_recap_counts_per_employee(client, world: World):
    _attendance(world, "member", "AUTO_VALID")
    _attendance(world, "leader", "PENDING_OM")
    month = jakarta_now().date().strftime("%Y-%m")

    hr = client.get("/recaps/attendance", headers=world.headers(client, "hr"), params={"month": month})
    assert hr.status_code == 200, hr.text
    rows = {r["employee_id"]: r for r in hr.json()["employees"]}
    assert (rows[world.employees["member"]]["days_present"], rows[world.employees["member"]]["auto_valid"]) == (1, 1)
    assert (rows[world.employees["leader"]]["days_present"], rows[world.employees["leader"]]["needs_review"]) == (0, 1)

    own = client.get("/recaps/attendance", headers=world.headers(client, "member"), params={"month": month})
    assert own.status_code == 200
    assert [r["employee_id"] for r in own.json()["employees"]] == [world.employees["member"]]
    bad = client.get("/recaps/attendance", headers=world.headers(client, "member"), params={"month": "2026-13"})
    assert bad.status_code == 422
