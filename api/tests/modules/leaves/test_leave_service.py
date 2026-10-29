"""
api/tests/modules/leaves/test_leave_service.py

Unit test logika bisnis dan aturan otorisasi cuti:
- Karyawan biasa mengajukan cuti untuk diri sendiri (sukses)
- Karyawan biasa dilarang mengajukan cuti atas nama karyawan lain (ForbiddenError)
- Pencegahan pengajuan tanggal bertabrakan (has_overlapping_leave -> ValidationError)
- Kuota cuti tahunan tidak mencukupi (QUOTA_EXCEEDED -> 422)
- Pencegahan self-approval cuti oleh pemohon sendiri (ForbiddenError)
- Peninjau bukan manajerial/HR/Admin (ForbiddenError)
- PM me-review cuti yang sudah disetujui PM (ALREADY_APPROVED_BY_PM -> 409)
- Refund kuota cuti tahunan saat persetujuan awal PM ditolak oleh HR
- Persetujuan cuti yang bertabrakan dengan jadwal tim wajib dikonfirmasi (LEAVE_CONFLICT -> 409)
- Pembatalan cuti: pemohon/HR/OM, hanya sebelum hari cuti berakhir, kuota dikembalikan
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.errors import AppError, ForbiddenError, ValidationError
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.leaves.schemas.leave_schema import LeaveCancel, LeaveCreate, LeaveReview
from app.modules.leaves.services.leave_service import LeaveService


@pytest.fixture(autouse=True)
def _silent_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tes unit memakai repo tiruan; notifikasi diuji terpisah di tests/modules/notifications."""
    monkeypatch.setattr(LeaveService, "_notify", lambda self: AsyncMock())


def make_user(role: str = "EMPLOYEE", employee_id: str | None = None) -> CurrentUser:
    eid = str(uuid4()) if employee_id is None else str(employee_id)
    return CurrentUser(
        user_id=str(uuid4()),
        organization_id=str(uuid4()),
        email="test@visiontech.co.id",
        role=role,
        roles=[role],
        session_id=str(uuid4()),
        permissions=[],
        employee_id=eid,
    )


def test_apply_leave_self_success():
    """Pengajuan cuti untuk diri sendiri berhasil."""
    async def run():
        repo = AsyncMock()
        repo.has_overlapping_leave.return_value = False
        repo.get_or_create_balance.return_value = MagicMock(remaining_quota=10)
        new_leave_id = uuid4()
        repo.insert_leave.return_value = new_leave_id
        repo.get_leave.return_value = MagicMock(leave_id=new_leave_id, status="PENDING")

        service = LeaveService(repo)
        user = make_user("EMPLOYEE")
        data = LeaveCreate(
            leave_type="ANNUAL",
            start_date=date(2026, 5, 4),
            end_date=date(2026, 5, 6),
            reason="Liburan tahunan bersama keluarga",
        )

        res = await service.apply(user, data)
        assert res.leave_id == new_leave_id
        repo.insert_leave.assert_called_once()
        repo.has_overlapping_leave.assert_called_once()

    asyncio.run(run())


def test_apply_leave_for_other_by_regular_employee_forbidden():
    """Karyawan biasa dilarang mengajukan cuti atas nama karyawan lain."""
    async def run():
        repo = AsyncMock()
        service = LeaveService(repo)
        user = make_user("EMPLOYEE")
        other_emp_id = uuid4()

        data = LeaveCreate(
            employee_id=other_emp_id,
            leave_type="ANNUAL",
            start_date=date(2026, 5, 4),
            end_date=date(2026, 5, 6),
            reason="Mencoba ajukan untuk orang lain",
        )

        with pytest.raises(ForbiddenError) as exc_info:
            await service.apply(user, data)
        assert "Hanya HR atau Admin" in str(exc_info.value)

    asyncio.run(run())


def test_apply_leave_overlapping_dates_rejected():
    """Pengajuan cuti dengan tanggal bertabrakan ditolak."""
    async def run():
        repo = AsyncMock()
        repo.has_overlapping_leave.return_value = True
        service = LeaveService(repo)
        user = make_user("EMPLOYEE")

        data = LeaveCreate(
            leave_type="ANNUAL",
            start_date=date(2026, 5, 4),
            end_date=date(2026, 5, 6),
            reason="Cuti bentrok",
        )

        with pytest.raises(ValidationError) as exc_info:
            await service.apply(user, data)
        assert "bertabrakan" in str(exc_info.value) or "sudah memiliki permohonan cuti aktif" in str(exc_info.value)

    asyncio.run(run())


def test_review_leave_unauthorized_role_forbidden():
    """Karyawan biasa tidak boleh me-review permohonan cuti."""
    async def run():
        repo = AsyncMock()
        service = LeaveService(repo)
        user = make_user("EMPLOYEE")
        leave_id = uuid4()

        data = LeaveReview(decision="APPROVED", note="Setuju")
        with pytest.raises(ForbiddenError) as exc_info:
            await service.review(user, leave_id, data)
        assert "berwenang meninjau" in str(exc_info.value)

    asyncio.run(run())


def test_review_leave_self_approval_forbidden():
    """Pemohon cuti dilarang menyetujui atau menolak permohonannya sendiri."""
    async def run():
        repo = AsyncMock()
        emp_id = uuid4()
        user = make_user("PROJECT_MANAGER", employee_id=emp_id)
        leave_id = uuid4()
        repo.get_leave.return_value = MagicMock(
            leave_id=leave_id,
            employee_id=emp_id,
            status="PENDING",
            leave_type="ANNUAL",
            total_days=3,
        )

        service = LeaveService(repo)
        data = LeaveReview(decision="APPROVED", note="Setuju diri sendiri")

        with pytest.raises(ForbiddenError) as exc_info:
            await service.review(user, leave_id, data)
        assert "tidak dapat menyetujui" in str(exc_info.value)

    asyncio.run(run())


def test_review_leave_pm_re_review_rejected():
    """PM tidak boleh me-review permohonan cuti yang sudah disetujui PM (menunggu HR)."""
    async def run():
        repo = AsyncMock()
        pm_user = make_user("PROJECT_MANAGER", employee_id=uuid4())
        leave_id = uuid4()
        repo.get_leave.return_value = MagicMock(
            leave_id=leave_id,
            employee_id=uuid4(),
            status="APPROVED_BY_PM",
            leave_type="ANNUAL",
            total_days=3,
        )
        repo.division_pm_of.return_value = pm_user.employee_id

        service = LeaveService(repo)
        data = LeaveReview(decision="APPROVED", note="Setuju lagi")

        with pytest.raises(AppError) as exc_info:
            await service.review(pm_user, leave_id, data)
        assert exc_info.value.code == "ALREADY_APPROVED_BY_PM"

    asyncio.run(run())


def test_review_leave_refund_when_hr_rejects_after_pm():
    """Ketika HR menolak cuti yang sebelumnya sudah disetujui PM, kuota cuti di-refund."""
    async def run():
        repo = AsyncMock()
        hr_user = make_user("ADMIN_HR_GA", employee_id=uuid4())
        emp_id = uuid4()
        leave_id = uuid4()
        repo.get_leave.return_value = MagicMock(
            leave_id=leave_id,
            employee_id=emp_id,
            status="APPROVED_BY_PM",
            leave_type="ANNUAL",
            total_days=4,
            start_date=date(2026, 6, 1),
        )

        service = LeaveService(repo)
        data = LeaveReview(decision="REJECTED", note="Ditolak oleh HR karena beban proyek")

        await service.review(hr_user, leave_id, data)

        # Memastikan saldo kuota cuti di-refund (-4 hari)
        repo.deduct_balance.assert_called_once_with(emp_id, 2026, -4)
        repo.update_review.assert_called_once()

    asyncio.run(run())


def test_employee_cannot_read_other_employees_leave():
    """Karyawan biasa hanya boleh membaca cuti & saldo miliknya sendiri (IDOR)."""
    async def run():
        repo = AsyncMock()
        user = make_user("EMPLOYEE", employee_id=uuid4())
        repo.get_leave.return_value = MagicMock(employee_id=uuid4())
        service = LeaveService(repo)
        with pytest.raises(ForbiddenError):
            await service.get(user, uuid4())
        with pytest.raises(ForbiddenError):
            await service.balance(user, uuid4(), 2026)

    asyncio.run(run())


def test_employee_list_is_forced_to_own_leaves():
    async def run():
        repo = AsyncMock()
        repo.list_leaves.return_value = []
        own = uuid4()
        service = LeaveService(repo)
        await service.list(make_user("EMPLOYEE", employee_id=own), employee_id=uuid4())
        assert repo.list_leaves.await_args.kwargs["employee_id"] == own

    asyncio.run(run())


def test_pm_cannot_review_leave_outside_division():
    async def run():
        repo = AsyncMock()
        pm_user = make_user("PROJECT_MANAGER", employee_id=uuid4())
        repo.get_leave.return_value = MagicMock(employee_id=uuid4(), status="PENDING", leave_type="ANNUAL")
        repo.division_pm_of.return_value = uuid4()  # PM lain
        service = LeaveService(repo)
        with pytest.raises(ForbiddenError):
            await service.review(pm_user, uuid4(), LeaveReview(decision="APPROVED", note=None))

    asyncio.run(run())


def _future_leave(status: str, *, employee_id, leave_type: str = "ANNUAL") -> MagicMock:
    today = jakarta_now().date()
    return MagicMock(
        leave_id=uuid4(), employee_id=employee_id, status=status, leave_type=leave_type,
        start_date=today + timedelta(days=28), end_date=today + timedelta(days=30), total_days=3,
    )


def _conflict_row(work_date, team: str = "Tim Alfa", status: str = "ONGOING") -> MagicMock:
    return MagicMock(plan_id=uuid4(), work_date=work_date, team_name=team, status=status)


def test_approval_blocked_when_leave_clashes_with_team_schedule():
    """Persetujuan cuti pada hari jadwal tim berjalan ditolak (409 LEAVE_CONFLICT) sampai dikonfirmasi."""
    async def run():
        repo = AsyncMock()
        leave = _future_leave("PENDING", employee_id=uuid4())
        repo.get_leave.return_value = leave
        repo.schedule_conflicts.return_value = [_conflict_row(leave.start_date)]

        with pytest.raises(AppError) as exc:
            await LeaveService(repo).review(
                make_user("ADMIN_HR_GA", employee_id=uuid4()), leave.leave_id, LeaveReview(decision="APPROVED"),
            )
        assert exc.value.code == "LEAVE_CONFLICT"
        assert exc.value.status == 409
        assert exc.value.details["conflicts"][0]["team_name"] == "Tim Alfa"
        assert exc.value.details["conflicts"][0]["work_date"] == leave.start_date.isoformat()
        repo.update_review.assert_not_awaited()
        repo.deduct_balance.assert_not_awaited()

    asyncio.run(run())


def test_acknowledged_conflict_approves_and_notifies_division_pm():
    """Setelah konflik dikonfirmasi, persetujuan berjalan dan PM divisi diberi tahu."""
    async def run():
        repo = AsyncMock()
        leave = _future_leave("PENDING", employee_id=uuid4(), leave_type="SICK")
        repo.get_leave.return_value = leave
        repo.schedule_conflicts.return_value = [_conflict_row(leave.start_date)]
        notifier = AsyncMock()
        notifier.employee_name.return_value = "Budi"
        service = LeaveService(repo)
        service._notify = lambda: notifier  # type: ignore[method-assign]

        await service.review(
            make_user("ADMIN_HR_GA", employee_id=uuid4()), leave.leave_id,
            LeaveReview(decision="APPROVED", acknowledge_conflicts=True),
        )
        repo.update_review.assert_awaited_once()
        kwargs = notifier.notify_division_managers.await_args.kwargs
        assert kwargs["roles"] == ("PROJECT_MANAGER",)
        assert kwargs["target"] == "leave"

    asyncio.run(run())


def test_approval_without_schedule_clash_skips_conflict_gate():
    async def run():
        repo = AsyncMock()
        leave = _future_leave("PENDING", employee_id=uuid4())
        repo.get_leave.return_value = leave
        repo.schedule_conflicts.return_value = []
        await LeaveService(repo).review(
            make_user("ADMIN_HR_GA", employee_id=uuid4()), leave.leave_id, LeaveReview(decision="APPROVED"),
        )
        repo.update_review.assert_awaited_once()

    asyncio.run(run())


def test_owner_cancels_hr_approved_annual_leave_with_refund():
    """Pemohon membatalkan cuti tahunan yang sudah disetujui HR; kuota dikembalikan dan alasan tersimpan."""
    async def run():
        user = make_user("EMPLOYEE")
        leave = _future_leave("APPROVED_BY_HR", employee_id=user.employee_id)
        repo = AsyncMock()
        repo.get_leave.return_value = leave
        await LeaveService(repo).cancel(user, leave.leave_id, LeaveCancel(reason="Rencana berubah"))
        repo.cancel_leave.assert_awaited_once_with(leave.leave_id, "Rencana berubah")
        repo.deduct_balance.assert_awaited_once_with(user.employee_id, leave.start_date.year, -3)

    asyncio.run(run())


def test_owner_cancels_pm_approved_annual_leave_with_refund():
    """Pemohon membatalkan cuti tahunan yang sudah disetujui PM; kuota dikembalikan."""
    async def run():
        user = make_user("EMPLOYEE")
        leave = _future_leave("APPROVED_BY_PM", employee_id=user.employee_id)
        repo = AsyncMock()
        repo.get_leave.return_value = leave
        await LeaveService(repo).cancel(user, leave.leave_id, LeaveCancel(reason="Batal ikut kegiatan"))
        repo.cancel_leave.assert_awaited_once()
        repo.deduct_balance.assert_awaited_once_with(user.employee_id, leave.start_date.year, -3)

    asyncio.run(run())


def test_hr_cancels_employee_leave_and_employee_is_notified():
    """HR dapat membatalkan cuti karyawan; karyawan pemohon diberi notifikasi beserta alasannya."""
    async def run():
        emp_id = uuid4()
        leave = _future_leave("APPROVED_BY_HR", employee_id=emp_id, leave_type="SICK")
        repo = AsyncMock()
        repo.get_leave.return_value = leave
        notifier = AsyncMock()
        notifier.employee_name.return_value = "Budi"
        service = LeaveService(repo)
        service._notify = lambda: notifier  # type: ignore[method-assign]

        await service.cancel(make_user("ADMIN_HR_GA", employee_id=uuid4()), leave.leave_id,
                             LeaveCancel(reason="Dibatalkan HR"))
        repo.cancel_leave.assert_awaited_once()
        repo.deduct_balance.assert_not_awaited()  # cuti sakit tidak memotong kuota
        notifier.notify_employees.assert_awaited_once()
        assert notifier.notify_employees.await_args.args[0] == [emp_id]

    asyncio.run(run())


def test_other_employee_cannot_cancel_leave():
    """Karyawan lain (bukan HR/OM) tidak boleh membatalkan cuti orang lain."""
    async def run():
        repo = AsyncMock()
        repo.get_leave.return_value = MagicMock(employee_id=str(uuid4()), status="PENDING")
        with pytest.raises(ForbiddenError):
            await LeaveService(repo).cancel(make_user("EMPLOYEE"), uuid4(), LeaveCancel(reason="Mencoba batal"))
        repo.cancel_leave.assert_not_awaited()

    asyncio.run(run())


def test_leave_cannot_be_cancelled_after_its_last_day():
    """Cuti yang hari terakhirnya sudah lewat tidak dapat dibatalkan lagi."""
    async def run():
        user = make_user("EMPLOYEE")
        past = jakarta_now().date() - timedelta(days=1)
        repo = AsyncMock()
        repo.get_leave.return_value = MagicMock(
            employee_id=user.employee_id, status="APPROVED_BY_HR", leave_type="ANNUAL",
            start_date=past - timedelta(days=2), end_date=past, total_days=3,
        )
        with pytest.raises(AppError) as exc:
            await LeaveService(repo).cancel(user, uuid4(), LeaveCancel(reason="Terlambat"))
        assert exc.value.code == "NOT_CANCELLABLE"
        repo.cancel_leave.assert_not_awaited()

    asyncio.run(run())


def test_rejected_or_cancelled_leave_cannot_be_cancelled_again():
    async def run():
        user = make_user("EMPLOYEE")
        for status in ("REJECTED", "CANCELLED"):
            repo = AsyncMock()
            repo.get_leave.return_value = _future_leave(status, employee_id=user.employee_id)
            with pytest.raises(AppError) as exc:
                await LeaveService(repo).cancel(user, uuid4(), LeaveCancel(reason="Ulang"))
            assert exc.value.code == "NOT_CANCELLABLE"

    asyncio.run(run())
