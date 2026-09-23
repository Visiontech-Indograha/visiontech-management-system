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

from app.services import attendance_monitor_service as monitor
from tests.conftest import login_headers, requires_db

pytestmark = requires_db

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


def _admin_with_employee(make_user):
    user = make_user("ADMIN")
    (emp_id,) = user.query(
        """INSERT INTO vms.employee (organization_id, employee_no, full_name, position, join_date)
           VALUES (%s, 'UJI-001', %s, 'Teknisi', '2026-01-05') RETURNING id""",
        (user.org_id, EMPLOYEE_NAME),
    )[0]
    return user, str(emp_id)


def _check_in(user, emp_id: str, work_date: str, face_result: str | None = None) -> None:
    # Status ditentukan trigger DB (server yang memutuskan); NEEDS_REVIEW dibuat lewat wajah NO_MATCH.
    user.query(
        """INSERT INTO vms.attendance (organization_id, employee_id, work_date, site_label, check_in_at, radius_m, face_result)
           VALUES (%s, %s, %s, 'Lokasi uji', %s::date + time '08:05', 100, %s)""",
        (user.org_id, emp_id, work_date, work_date, face_result),
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
    for i in range(4):
        (emp,) = user.query(
            """INSERT INTO vms.employee (organization_id, employee_no, full_name, position, join_date)
               VALUES (%s, %s, 'Anggota uji', 'Teknisi', '2026-01-05') RETURNING id""",
            (user.org_id, f"UJI-1{i}"),
        )[0]
        _check_in(user, str(emp), "2026-09-23", "NO_MATCH")
    _at(monkeypatch, "2026-09-23T14:00:00")

    response = client.post("/cron/attendance/alert-needs-review", headers=login_headers(client, user))

    assert response.status_code == 200, response.text
    assert response.json()["needs_review_today"] == 4
    assert response.json()["alerted"] is True
    assert len(sent) == 1


def test_needs_review_below_minimum_is_quiet(client, make_user, sent, monkeypatch):
    user, emp_id = _admin_with_employee(make_user)
    _check_in(user, emp_id, "2026-09-23", "NO_MATCH")
    _at(monkeypatch, "2026-09-23T14:00:00")

    response = client.post("/cron/attendance/alert-needs-review", headers=login_headers(client, user))

    assert response.json()["alerted"] is False
    assert sent == []


@pytest.mark.parametrize("role", ["OPS", "FINANCE", None])
def test_only_admin_may_trigger_jobs(client, make_user, sent, role):
    headers = login_headers(client, make_user(role))

    assert client.post("/cron/attendance/alert-missing", headers=headers).status_code == 403
    assert client.post("/cron/attendance/alert-needs-review", headers=headers).status_code == 403
    assert sent == []
