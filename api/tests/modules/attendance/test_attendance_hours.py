"""
api/tests/test_attendance_hours.py
Pengujian unit dan aturan bisnis untuk jam operasional absensi:
- Jam masuk dibuka mulai pukul 06:45 (sebelum 06:45 ditolak CHECKIN_TOO_EARLY)
- Waktu kerja 9 jam kotor (8 jam efektif + 1 jam istirahat):
  - < 9 jam kotor: dicatat pulang cepat dan ada keterangan durasi kerja
  - >= 9 jam kotor: absensi valid penuh dan ada pesan penyemangat
- Batas check-out mandiri ditutup pukul 19:00 (setelah 19:00 ditolak CHECKOUT_CLOSED)
- Auto check-out pada pukul 19:00 untuk sesi yang belum selesai (keterangan: Lupa absen pulang)
"""
from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.modules.attendance.services.attendance_monitor_service import AttendanceMonitorService
from app.modules.attendance.services.attendance_session_service import AttendanceSessionService

MONITOR = "app.modules.attendance.services.attendance_monitor_service"


def test_check_in_before_0645_is_rejected():
    """Percobaan check-in sebelum pukul 06:45 ditolak dengan 422 CHECKIN_TOO_EARLY."""
    async def run():
        repo = AsyncMock()
        clock = AsyncMock()
        service = AttendanceSessionService(repo, clock)

        user_id = str(uuid4())
        org_id = str(uuid4())
        site_id = uuid4()

        worker_mock = MagicMock(employee_id=uuid4(), attendance_mode="OFFICE", unit_id=None, is_admin=False)
        repo.attendance_mode_of.return_value = worker_mock

        early_dt = datetime(2026, 10, 14, 6, 44, tzinfo=UTC)
        clock_mock = MagicMock()
        clock_mock.local_now = early_dt
        clock_mock.today = early_dt.date()
        clock.local_now.return_value = clock_mock

        with pytest.raises(AppError) as exc_info:
            await service.check_in(
                org_id,
                user_id,
                site_id=site_id,
                lng=106.8,
                lat=-6.2,
                origin="GPS",
                selfie_file_id=uuid4(),  # V2: swafoto selalu wajib, diperiksa sebelum jam buka
                channel="WEB",
                at=early_dt,
            )

        assert exc_info.value.code == "CHECKIN_TOO_EARLY"
        assert exc_info.value.status == 422
        assert "06:45" in exc_info.value.message

    asyncio.run(run())


def test_check_out_after_1900_is_rejected():
    """Percobaan check-out setelah pukul 19:00 ditolak dengan 422 CHECKOUT_CLOSED."""
    async def run():
        repo = AsyncMock()
        clock = AsyncMock()
        service = AttendanceSessionService(repo, clock)

        user_id = str(uuid4())
        org_id = str(uuid4())

        worker_mock = MagicMock(employee_id=uuid4(), attendance_mode="OFFICE", unit_id=None, is_admin=False)
        repo.attendance_mode_of.return_value = worker_mock

        check_in_at = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
        session_mock = MagicMock(
            id=uuid4(),
            employee_id=worker_mock.employee_id,
            organization_id=org_id,
            check_in_at=check_in_at,
            status="AUTO_VALID",
        )
        repo.open_session.return_value = session_mock
        repo.active_leader_plan_without_report.return_value = None

        late_dt = datetime(2026, 10, 14, 19, 15, tzinfo=UTC)
        clock_mock = MagicMock()
        clock_mock.local_now = late_dt
        clock_mock.today = late_dt.date()
        clock.local_now.return_value = clock_mock

        with pytest.raises(AppError) as exc_info:
            await service.check_out(
                user_id,
                channel="WEB",
                org_id=org_id,
            )

        assert exc_info.value.code == "CHECKOUT_CLOSED"
        assert exc_info.value.status == 422
        assert "19:00" in exc_info.value.message

    asyncio.run(run())


def test_check_out_under_9_hours_records_early_leave():
    """Check-out dengan durasi < 9 jam kotor (< 8 jam efektif) mencatat keterangan pulang cepat."""
    async def run():
        repo = AsyncMock()
        clock = AsyncMock()
        service = AttendanceSessionService(repo, clock)

        user_id = str(uuid4())
        org_id = str(uuid4())

        worker_mock = MagicMock(employee_id=uuid4(), attendance_mode="OFFICE", unit_id=None, is_admin=False)
        repo.attendance_mode_of.return_value = worker_mock

        check_in_at = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
        session_mock = MagicMock(
            id=uuid4(),
            employee_id=worker_mock.employee_id,
            organization_id=org_id,
            check_in_at=check_in_at,
            status="AUTO_VALID",
        )
        repo.open_session.return_value = session_mock
        repo.active_leader_plan_without_report.return_value = None

        now_dt = datetime(2026, 10, 14, 14, 0, tzinfo=UTC)
        clock_mock = MagicMock()
        clock_mock.local_now = now_dt
        clock_mock.today = now_dt.date()
        clock.local_now.return_value = clock_mock

        repo.active_leader_plan_without_report.return_value = None
        closed_row_mock = MagicMock()
        closed_row_mock._mapping = {"id": session_mock.id, "check_out_outside": False}
        repo.close.return_value = closed_row_mock
        repo.reviewer_employee_ids.return_value = []

        res = await service.check_out(user_id, channel="WEB", org_id=org_id)

        call_args = repo.close.call_args[1]
        assert "Pulang Cepat" in call_args["explanation"]
        assert "5 jam 0 menit" in call_args["explanation"]
        assert res.encouragement_message is None

    asyncio.run(run())


def test_check_out_uses_wib_for_naive_database_clock():
    """Timestamp WIB tanpa zona dari database tidak boleh ditafsirkan sebagai UTC."""
    async def run():
        repo = AsyncMock()
        clock = AsyncMock()
        service = AttendanceSessionService(repo, clock)
        employee_id = uuid4()
        org_id = str(uuid4())
        repo.attendance_mode_of.return_value = MagicMock(
            employee_id=employee_id, attendance_mode="OFFICE", unit_id=None, is_admin=False
        )
        repo.open_session.return_value = MagicMock(
            id=uuid4(),
            employee_id=employee_id,
            organization_id=org_id,
            check_in_at=datetime(2026, 10, 14, 7, 0, tzinfo=UTC),
            status="AUTO_VALID",
        )
        clock.local_now.return_value = MagicMock(local_now=datetime(2026, 10, 14, 14, 30, tzinfo=UTC))
        repo.active_leader_plan_without_report.return_value = None
        repo.close.return_value = MagicMock(_mapping={"check_out_outside": False})
        repo.reviewer_employee_ids.return_value = []

        await service.check_out("user", channel="WEB", org_id=org_id)

        explanation = repo.close.call_args.kwargs["explanation"]
        assert "Pulang Cepat" in explanation
        assert "6 jam 30 menit" in explanation

    asyncio.run(run())


def test_check_out_full_hours_gives_encouragement_message():
    """Check-out dengan durasi >= 9 jam kotor (>= 8 jam efektif) menyertakan pesan penyemangat."""
    async def run():
        repo = AsyncMock()
        clock = AsyncMock()
        service = AttendanceSessionService(repo, clock)

        user_id = str(uuid4())
        org_id = str(uuid4())

        worker_mock = MagicMock(employee_id=uuid4(), attendance_mode="OFFICE", unit_id=None, is_admin=False)
        repo.attendance_mode_of.return_value = worker_mock

        check_in_at = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
        session_mock = MagicMock(
            id=uuid4(),
            employee_id=worker_mock.employee_id,
            organization_id=org_id,
            check_in_at=check_in_at,
            status="AUTO_VALID",
        )
        repo.open_session.return_value = session_mock
        repo.active_leader_plan_without_report.return_value = None

        now_dt = datetime(2026, 10, 14, 17, 30, tzinfo=UTC)
        clock_mock = MagicMock()
        clock_mock.local_now = now_dt
        clock_mock.today = now_dt.date()
        clock.local_now.return_value = clock_mock

        repo.active_leader_plan_without_report.return_value = None
        closed_row_mock = MagicMock()
        closed_row_mock._mapping = {"id": session_mock.id, "check_out_outside": False}
        repo.close.return_value = closed_row_mock
        repo.reviewer_employee_ids.return_value = []

        with patch("app.modules.attendance.services.attendance_session_service.NotificationService") as mock_notif_cls:
            mock_notif = mock_notif_cls.return_value
            mock_notif.attendance_encouragement = AsyncMock()
            res = await service.check_out(user_id, channel="WEB", org_id=org_id)
            mock_notif.attendance_encouragement.assert_awaited_once()

        call_args = repo.close.call_args[1]
        assert call_args["explanation"] is None
        assert res.encouragement_message is not None
        assert "Terima kasih atas kerja keras" in res.encouragement_message

    asyncio.run(run())


def test_auto_checkout_unclosed_sessions():
    """Auto-checkout menutup sesi terbuka hari ini pada pukul 19:00 dengan keterangan lupa absen pulang."""
    async def run():
        repo = AsyncMock()
        service = AttendanceMonitorService(repo)

        org_id = str(uuid4())
        closed_mock = [MagicMock(employee_id=uuid4(), site_label="Kantor Pusat")]

        with patch(f"{MONITOR}.CRUDAttendanceSession") as mock_session_cls, \
             patch(f"{MONITOR}.NotificationService") as mock_notif_cls, \
             patch(f"{MONITOR}.jakarta_now") as mock_now:

            mock_now.return_value = datetime(2026, 10, 14, 19, 5, tzinfo=UTC)
            mock_session = mock_session_cls.return_value
            mock_session.auto_checkout_unclosed = AsyncMock(return_value=closed_mock)
            mock_notif = mock_notif_cls.return_value
            mock_notif.attendance_auto_checkout_bulk = AsyncMock()

            count = await service.auto_checkout_unclosed_sessions(org_id)
            assert count == 1
            mock_session.auto_checkout_unclosed.assert_awaited_once()
            mock_notif.attendance_auto_checkout_bulk.assert_awaited_once()

    asyncio.run(run())


def _hints_service(opened, pending):
    repo = AsyncMock()
    repo.open_hint.return_value = opened
    repo.unreported_items.return_value = pending
    clock = AsyncMock()
    clock.local_now.return_value = MagicMock(today=date(2026, 10, 26))
    return AttendanceSessionService(repo, clock)


def test_required_out_is_nine_hours_after_on_time_check_in():
    from datetime import time, timedelta

    from app.core.time import WIB
    checked_in = datetime(2026, 10, 26, 7, 0, tzinfo=WIB)
    opened = MagicMock(clock_in_at=checked_in, scheduled_out=time(17, 0), is_late=False)
    _, required_out, _, _ = asyncio.run(_hints_service(opened, None).day_hints("org", str(uuid4())))
    assert required_out == checked_in + timedelta(hours=9)


def test_late_check_in_must_leave_at_office_closing_time():
    from datetime import time

    from app.core.time import WIB
    opened = MagicMock(clock_in_at=datetime(2026, 10, 26, 8, 30, tzinfo=WIB), scheduled_out=time(17, 0), is_late=True)
    _, required_out, _, _ = asyncio.run(_hints_service(opened, None).day_hints("org", str(uuid4())))
    assert required_out == datetime(2026, 10, 26, 17, 0, tzinfo=WIB)


def test_day_hints_reports_pending_daily_report_and_no_session():
    plan_id = uuid4()
    pending = MagicMock(n=2, plan_id=plan_id)
    _, required_out, count, plan = asyncio.run(_hints_service(None, pending).day_hints("org", str(uuid4())))
    assert required_out is None and count == 2 and plan == plan_id
    _, _, none_count, _ = asyncio.run(_hints_service(None, None).day_hints("org", None))
    assert none_count == 0
