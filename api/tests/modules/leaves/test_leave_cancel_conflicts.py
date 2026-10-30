"""
api/tests/modules/leaves/test_leave_cancel_conflicts.py

Uji integrasi (basis data) untuk:
- F6: persetujuan cuti yang bertabrakan dengan jadwal tim APPROVED/ONGOING wajib dikonfirmasi (409 LEAVE_CONFLICT)
- F7: pembatalan cuti yang sudah disetujui; status CANCELLED tidak lagi memblokir absensi
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.database.session import AsyncSessionLocal
from app.modules.attendance.repositories.attendance_session_repository import AttendanceSessionRepository
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _next_workday(days_ahead: int) -> str:
    day = datetime.now(UTC).date() + timedelta(days=days_ahead)
    while day.weekday() == 6:
        day += timedelta(days=1)
    return day.isoformat()


def _plan(world: World, work_date: str, status: str) -> None:
    sync_query(
        "INSERT INTO work_plan_daily (division_id, team_id, work_date, site_name, site_lat, site_lng, status, "
        "created_by_id) VALUES (%s, %s, %s, 'Lokasi uji', -6.2, 106.8, %s, %s)",
        (world.unit_id, world.team_id, work_date, status, world.employees["leader"]),
    )


def _on_approved_leave(employee_id: str, work_date: str) -> bool:
    async def run() -> bool:
        async with AsyncSessionLocal() as db:
            on_leave, _ = await AttendanceSessionRepository(db).is_on_approved_leave(
                employee_id, datetime.fromisoformat(work_date).date()
            )
            return on_leave

    return asyncio.run(run())


def _apply_sick(client, world: World, work_date: str) -> str:
    response = client.post(
        "/leaves", headers=world.headers(client, "member"),
        json={"leave_type": "SICK", "start_date": work_date, "end_date": work_date, "reason": "Demam uji"},
    )
    assert response.status_code == 201, response.text
    return response.json()["leave_id"]


def test_approval_requires_acknowledging_schedule_conflicts(client, world: World):
    work_date = _next_workday(60)
    _plan(world, work_date, "APPROVED")
    leave_id = _apply_sick(client, world, work_date)

    detail = client.get(f"/leaves/{leave_id}", headers=world.headers(client, "hr")).json()
    assert len(detail["conflicts"]) == 1
    assert detail["conflicts"][0]["work_date"] == work_date
    assert detail["conflicts"][0]["status"] == "APPROVED"

    refused = client.post(f"/leaves/{leave_id}/review", headers=world.headers(client, "hr"),
                          json={"decision": "APPROVED"})
    assert refused.status_code == 409, refused.text
    error = refused.json()["error"]
    assert error["code"] == "LEAVE_CONFLICT"
    assert error["details"]["conflicts"][0]["work_date"] == work_date
    assert client.get(f"/leaves/{leave_id}", headers=world.headers(client, "hr")).json()["status"] == "PENDING"

    approved = client.post(f"/leaves/{leave_id}/review", headers=world.headers(client, "hr"),
                           json={"decision": "APPROVED", "acknowledge_conflicts": True})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED_BY_HR"


def test_cancelled_approved_leave_no_longer_blocks_attendance(client, world: World):
    work_date = _next_workday(61)
    leave_id = _apply_sick(client, world, work_date)
    approved = client.post(f"/leaves/{leave_id}/review", headers=world.headers(client, "hr"),
                           json={"decision": "APPROVED"})
    assert approved.status_code == 200, approved.text
    member_id = world.employees["member"]
    assert _on_approved_leave(member_id, work_date) is True

    too_short = client.post(f"/leaves/{leave_id}/cancel", headers=world.headers(client, "member"),
                            json={"reason": "ok"})
    assert too_short.status_code == 422, too_short.text

    cancelled = client.post(f"/leaves/{leave_id}/cancel", headers=world.headers(client, "member"),
                            json={"reason": "Sudah sembuh, masuk kerja"})
    assert cancelled.status_code == 200, cancelled.text
    body = cancelled.json()
    assert body["status"] == "CANCELLED"
    assert body["cancel_note"] == "Sudah sembuh, masuk kerja"
    assert _on_approved_leave(member_id, work_date) is False

    again = client.post(f"/leaves/{leave_id}/cancel", headers=world.headers(client, "member"),
                        json={"reason": "Batal dua kali"})
    assert again.status_code == 409, again.text
    assert again.json()["error"]["code"] == "NOT_CANCELLABLE"


def test_hr_can_cancel_employee_leave(client, world: World):
    work_date = _next_workday(62)
    leave_id = _apply_sick(client, world, work_date)
    cancelled = client.post(f"/leaves/{leave_id}/cancel", headers=world.headers(client, "hr"),
                            json={"reason": "Dibatalkan oleh HR"})
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"


def test_cancel_without_body_still_works_for_older_field_apps(client, world: World):
    """APK lapangan lama membatalkan cuti tanpa body; permintaan tetap berhasil (alasan kosong)."""
    work_date = _next_workday(63)
    leave_id = _apply_sick(client, world, work_date)
    cancelled = client.post(f"/leaves/{leave_id}/cancel", headers=world.headers(client, "member"))
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancel_note"] is None


def test_approval_note_is_not_reported_as_rejection(client, world: World):
    """T-8: catatan persetujuan (kolom rejection_note bersama) muncul sebagai review_note, bukan penolakan."""
    hr = world.headers(client, "hr")
    approved_id = _apply_sick(client, world, _next_workday(70))
    approved = client.post(f"/leaves/{approved_id}/review", headers=hr,
                           json={"decision": "APPROVED", "note": "Semoga cepat sembuh"})
    assert approved.status_code == 200, approved.text
    detail = client.get(f"/leaves/{approved_id}", headers=hr).json()
    assert detail["review_note"] == "Semoga cepat sembuh"
    assert detail["rejection_note"] is None

    rejected_id = _apply_sick(client, world, _next_workday(71))
    rejected = client.post(f"/leaves/{rejected_id}/review", headers=hr,
                           json={"decision": "REJECTED", "note": "Surat dokter tidak lengkap"})
    assert rejected.status_code == 200, rejected.text
    detail = client.get(f"/leaves/{rejected_id}", headers=hr).json()
    assert detail["rejection_note"] == "Surat dokter tidak lengkap"
    assert detail["review_note"] is None
