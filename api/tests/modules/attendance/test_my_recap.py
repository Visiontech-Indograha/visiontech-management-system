"""
Rekap absensi bulanan milik sendiri (GET /attendance/me/recap): hanya data pemilik akun, uang makan hanya dari
absensi sah, hitung terlambat (> 08:00 WIB) dan pulang awal.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _attend(emp_id: str, day: str, *, clock_in: str, clock_out: str | None, status: str, meal: int) -> None:
    sync_query(
        "INSERT INTO attendance (employee_id, attendance_date, target_location_type, office_id, scheduled_in, "
        "scheduled_out, clock_in_at, clock_out_at, in_lat, in_lng, face_match_score, face_photo_path, "
        "distance_to_target_m, is_within_attendance_radius, om_approval_status, distance_from_main_office_m, "
        "city_zone_status, meal_allowance_amount) "
        "VALUES (%s, %s, 'OFFICE', (SELECT office_id FROM employee WHERE employee_id = %s), '08:00', '17:00', "
        "(%s::date + %s::time) AT TIME ZONE 'Asia/Jakarta', "
        "CASE WHEN %s::text IS NULL THEN NULL ELSE (%s::date + %s::time) AT TIME ZONE 'Asia/Jakarta' END, "
        "-6.2, 106.8, 0, 'uji.webp', 0, TRUE, %s, 0, 'DALAM_KOTA', %s) RETURNING 1",
        (emp_id, day, emp_id, day, clock_in, clock_out, day, clock_out, status, meal),
    )


def test_recap_counts_late_early_and_valid_meal_only(client, world: World):
    member = world.employees["member"]
    _attend(member, "2026-03-02", clock_in="07:50", clock_out="17:05", status="AUTO_VALID", meal=35000)
    _attend(member, "2026-03-03", clock_in="08:20", clock_out="16:30", status="AUTO_VALID", meal=35000)
    _attend(member, "2026-03-04", clock_in="07:55", clock_out=None, status="PENDING_OM", meal=35000)

    response = client.get("/attendance/me/recap", params={"month": "2026-03"},
                          headers=world.headers(client, "member"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["month"] == "2026-03"
    assert body["days_present"] == 3
    assert body["late_days"] == 1
    assert body["early_leave_days"] == 1
    assert body["pending_days"] == 1
    assert body["meal_allowance_total"] == 70000
    assert [item["work_date"] for item in body["items"]] == ["2026-03-04", "2026-03-03", "2026-03-02"]


def test_recap_never_shows_other_employees(client, world: World):
    _attend(world.employees["leader"], "2026-03-02", clock_in="07:50", clock_out="17:05",
            status="AUTO_VALID", meal=35000)
    body = client.get("/attendance/me/recap", params={"month": "2026-03"},
                      headers=world.headers(client, "member")).json()
    assert body["days_present"] == 0 and body["items"] == []


@pytest.mark.parametrize("month", ["2026-13", "26-03", "abc"])
def test_recap_rejects_bad_month(client, world: World, month: str):
    response = client.get("/attendance/me/recap", params={"month": month}, headers=world.headers(client, "member"))
    assert response.status_code in (400, 422)
