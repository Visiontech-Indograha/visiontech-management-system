"""
T-08 · Peringatan bisnis absensi → #vms-alerts (dok 17 §5.3, P4-9).
- Tidak ada absensi masuk SAMA SEKALI sampai 09.00 WIB (hari kerja) → peringatan.
- NEEDS_REVIEW hari ini > 2× rata-rata harian 14 hari terakhir (minimal 3) → peringatan.
Pesan tidak boleh memuat data pribadi (dok 17 §2); hanya ADMIN yang boleh memicu.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.modules.attendance.services import attendance_monitor_service as monitor
from tests.conftest import login_headers, requires_db, sync_query

# Tes ini menghitung absensi tanggal tetap lintas kantor + memakai employee_no "UJI-001": satu worker saja (xdist).
pytestmark = [requires_db, pytest.mark.xdist_group("attendance_monitor")]

WIB = ZoneInfo("Asia/Jakarta")
EMPLOYEE_NAME = "Rusyidi Siregar Uji"


@pytest.fixture
def sent(monkeypatch) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []

    async def fake_alert(title: str, description: str) -> None:
        calls.append((title, description))

    monkeypatch.setattr(monitor, "send_business_alert", fake_alert)
    return calls


def _at(monkeypatch, iso: str) -> None:
    monkeypatch.setattr(monitor, "jakarta_now", lambda: datetime.fromisoformat(iso).replace(tzinfo=WIB))


def _employee_of(user) -> str:
    return str(sync_query("SELECT employee_id FROM users WHERE user_id = %s", (user.user_id,))[0][0])


def _admin_with_employee(make_user):
    user = make_user("ADMIN")
    emp_id = _employee_of(user)
    sync_query("UPDATE employee SET full_name = %s, employee_no = 'UJI-001' WHERE employee_id = %s RETURNING 1",
               (EMPLOYEE_NAME, emp_id))
    return user, emp_id


def _check_in(user, emp_id: str, work_date: str, needs_review: bool = False) -> None:
    sync_query(
        "INSERT INTO attendance (employee_id, attendance_date, target_location_type, office_id, scheduled_in, "
        "scheduled_out, clock_in_at, in_lat, in_lng, face_match_score, face_photo_path, distance_to_target_m, "
        "is_within_attendance_radius, om_approval_status, distance_from_main_office_m, city_zone_status, "
        "meal_allowance_amount) "
        "VALUES (%s, %s, 'OFFICE', (SELECT office_id FROM employee WHERE employee_id = %s), '07:00', '16:00', "
        "%s::date + time '08:05', -6.2, 106.8, 0, 'uji.webp', 0, TRUE, %s, 0, 'DALAM_KOTA', 0) RETURNING 1",
        (emp_id, work_date, emp_id, work_date, "PENDING_OM" if needs_review else "AUTO_VALID"),
    )


def test_no_check_in_by_nine_raises_alert_without_personal_data(client, make_user, sent, monkeypatch):
    user, _ = _admin_with_employee(make_user)
    _at(monkeypatch, "2026-09-23T09:05:00")

    response = client.post("/cron/attendance/alert-missing", headers=login_headers(client, user))

    assert response.status_code == 200, response.text
    assert response.json()["alerted"] is True
    assert len(sent) == 1
    assert EMPLOYEE_NAME not in sent[0][1] and "UJI-001" not in sent[0][1]
    assert "09.05 WIB" in sent[0][1]


def test_any_check_in_means_no_alert(client, make_user, sent, monkeypatch):
    user, emp_id = _admin_with_employee(make_user)
    _check_in(user, emp_id, "2026-09-23")
    _at(monkeypatch, "2026-09-23T09:05:00")

    response = client.post("/cron/attendance/alert-missing", headers=login_headers(client, user))

    assert response.json() == {"alerted": False, "check_ins_today": 1}
    assert sent == []


@pytest.mark.parametrize("iso", ["2026-09-23T08:59:00", "2026-09-26T10:00:00"])  # sebelum 09.00; Sabtu
def test_before_nine_or_weekend_is_skipped(client, make_user, sent, monkeypatch, iso):
    user, _ = _admin_with_employee(make_user)
    _at(monkeypatch, iso)

    response = client.post("/cron/attendance/alert-missing", headers=login_headers(client, user))

    assert response.json()["alerted"] is False
    assert sent == []


def test_needs_review_spike_alerts(client, make_user, sent, monkeypatch):
    user, _ = _admin_with_employee(make_user)
    for _ in range(4):
        _check_in(user, _employee_of(make_user(None)), "2026-09-23", needs_review=True)
    _at(monkeypatch, "2026-09-23T14:00:00")

    response = client.post("/cron/attendance/alert-needs-review", headers=login_headers(client, user))

    assert response.status_code == 200, response.text
    assert response.json()["needs_review_today"] == 4
    assert response.json()["alerted"] is True
    assert len(sent) == 1


def test_needs_review_below_minimum_is_quiet(client, make_user, sent, monkeypatch):
    user, emp_id = _admin_with_employee(make_user)
    _check_in(user, emp_id, "2026-09-23", needs_review=True)
    _at(monkeypatch, "2026-09-23T14:00:00")

    response = client.post("/cron/attendance/alert-needs-review", headers=login_headers(client, user))

    assert response.json()["alerted"] is False
    assert sent == []


@pytest.mark.parametrize("role", ["OPS", "HR", None])
def test_only_admin_may_trigger_jobs(client, make_user, sent, role):
    headers = login_headers(client, make_user(role))

    assert client.post("/cron/attendance/alert-missing", headers=headers).status_code == 403
    assert client.post("/cron/attendance/alert-needs-review", headers=headers).status_code == 403
    assert sent == []
