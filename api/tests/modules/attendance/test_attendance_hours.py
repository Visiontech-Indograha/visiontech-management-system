"""
api/tests/test_attendance_hours.py
Pengujian unit dan aturan bisnis untuk jam operasional absensi:
- Jam masuk dibuka mulai pukul 07:00 (sebelum 07:00 ditolak CHECKIN_TOO_EARLY)
- Waktu kerja 9 jam kotor (8 jam efektif + 1 jam istirahat):
  - < 9 jam kotor: dicatat pulang cepat dan ada keterangan durasi kerja
  - >= 9 jam kotor: absensi valid penuh dan ada pesan penyemangat
- Batas check-out mandiri ditutup pukul 19:00 (setelah 19:00 ditolak CHECKOUT_CLOSED)
- Auto check-out pada pukul 19:00 untuk sesi yang belum selesai (keterangan: Lupa absen pulang)
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.modules.attendance.services.attendance_monitor_service import AttendanceMonitorService
from app.modules.attendance.services.attendance_session_service import AttendanceSessionService

MONITOR = "app.modules.attendance.services.attendance_monitor_service"


def test_check_in_before_0700_is_rejected():
    """Percobaan check-in sebelum pukul 07:00 ditolak dengan 422 CHECKIN_TOO_EARLY."""
    async def run():
        repo = AsyncMock()
        clock = AsyncMock()
        service = AttendanceSessionService(repo, clock)

        user_id = str(uuid4())
        org_id = str(uuid4())
        site_id = uuid4()

        worker_mock = MagicMock(employee_id=uuid4(), attendance_mode="OFFICE", unit_id=None, is_admin=False)
        repo.attendance_mode_of.return_value = worker_mock

        early_dt = datetime(2026, 10, 14, 6, 45, tzinfo=UTC)
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
                selfie_file_id=None,
                channel="WEB",
                at=early_dt,
            )

        assert exc_info.value.code == "CHECKIN_TOO_EARLY"
        assert exc_info.value.status == 422
        assert "07:00" in exc_info.value.message

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

        now_dt = datetime(2026, 10, 14, 14, 0, tzinfo=UTC)
        clock_mock = MagicMock()
        clock_mock.local_now = now_dt
        clock_mock.today = now_dt.date()
        clock.local_now.return_value = clock_mock

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

        now_dt = datetime(2026, 10, 14, 17, 30, tzinfo=UTC)
        clock_mock = MagicMock()
        clock_mock.local_now = now_dt
        clock_mock.today = now_dt.date()
        clock.local_now.return_value = clock_mock

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
