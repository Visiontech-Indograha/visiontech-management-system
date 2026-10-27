"""
app/modules/leaves/services/leave_service.py

Service logika bisnis cuti, izin, dan sakit.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.modules.leaves.repositories.leave_repository import LeaveRepository
from app.modules.leaves.schemas.leave_schema import LeaveCreate, LeaveReview


class LeaveService:
    """Logika alur persetujuan cuti dan pengurangan kuota."""

    def __init__(self, repo: LeaveRepository) -> None:
        self.repo = repo

    async def apply(self, user: CurrentUser, data: LeaveCreate) -> Any:
        emp_id = data.employee_id or user.employee_id
        if emp_id is None:
            raise ValidationError("Karyawan pemohon cuti wajib ditentukan.")

        if data.end_date < data.start_date:
            raise ValidationError("Tanggal akhir cuti tidak boleh sebelum tanggal mulai.")

        total_days = (data.end_date - data.start_date).days + 1
        year = data.start_date.year

        if data.leave_type == "ANNUAL":
            bal = await self.repo.get_or_create_balance(emp_id, year)
            if bal.remaining_quota < total_days:
                raise AppError(
                    "QUOTA_EXCEEDED",
                    f"Sisa kuota cuti tahunan ({bal.remaining_quota} hari) tidak mencukupi untuk "
                    f"pengajuan {total_days} hari.",
                    status=422,
                )

        leave_id = await self.repo.insert_leave(
            employee_id=emp_id,
            leave_type=data.leave_type,
            start_date=data.start_date,
            end_date=data.end_date,
            total_days=total_days,
            reason=data.reason.strip(),
            attachment_path=str(data.attachment_file_id) if data.attachment_file_id else None,
            status="PENDING",
        )
        return await self.repo.get_leave(leave_id)

    async def review(self, user: CurrentUser, leave_id: UUID, data: LeaveReview) -> Any:
        leave = await self.repo.get_leave(leave_id)
        if leave is None:
            raise NotFoundError("Permohonan cuti")

        if leave.status in ("APPROVED_BY_HR", "REJECTED", "CANCELLED"):
            raise AppError("ALREADY_DECIDED", "Permohonan cuti ini sudah diputuskan.", status=409)

        is_pm = user.role == "PROJECT_MANAGER"
        new_status = "REJECTED" if data.decision == "REJECTED" else ("APPROVED_BY_PM" if is_pm else "APPROVED_BY_HR")

        reviewer_id = user.employee_id or user.user_id

        await self.repo.update_review(
            leave_id=leave_id,
            status=new_status,
            reviewer_id=reviewer_id,
            is_pm=is_pm,
            note=data.note.strip() if data.note else None,
        )

        # Potong kuota cuti tahunan saat disetujui (PM atau HR)
        if data.decision == "APPROVED" and leave.leave_type == "ANNUAL":
            await self.repo.deduct_balance(leave.employee_id, leave.start_date.year, leave.total_days)

        return await self.repo.get_leave(leave_id)

    async def get(self, leave_id: UUID) -> Any:
        leave = await self.repo.get_leave(leave_id)
        if leave is None:
            raise NotFoundError("Permohonan cuti")
        return leave

    async def list(
        self,
        *,
        employee_id: UUID | None = None,
        status: str | None = None,
        year: int | None = None,
    ) -> list[Any]:
        return list(await self.repo.list_leaves(employee_id=employee_id, status=status, year=year))

    async def balance(self, employee_id: UUID, year: int) -> Any:
        bal = await self.repo.get_or_create_balance(employee_id, year)
        return bal
