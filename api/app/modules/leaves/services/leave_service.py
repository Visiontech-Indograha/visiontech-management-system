"""
app/modules/leaves/services/leave_service.py

Service logika bisnis cuti, izin, dan sakit.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.modules.leaves.repositories.leave_repository import LeaveRepository
from app.modules.leaves.schemas.leave_schema import LeaveCreate, LeaveReview

ALLOWED_REVIEW_ROLES = ("PROJECT_MANAGER", "ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN")


class LeaveService:
    """Logika alur persetujuan cuti dan pengurangan kuota."""

    def __init__(self, repo: LeaveRepository) -> None:
        self.repo = repo

    async def apply(self, user: CurrentUser, data: LeaveCreate) -> Any:
        # Karyawan biasa hanya boleh mengajukan cuti untuk dirinya sendiri
        emp_id: UUID | str | None
        if user.role not in ("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "SUPER_ADMIN"):
            if data.employee_id and str(data.employee_id) != str(user.employee_id):
                raise ForbiddenError("Hanya HR atau Admin yang dapat mengajukan cuti atas nama karyawan lain.")
            emp_id = user.employee_id
        else:
            emp_id = data.employee_id or user.employee_id

        if emp_id is None:
            raise ValidationError("Karyawan pemohon cuti wajib ditentukan.")

        if data.end_date < data.start_date:
            raise ValidationError("Tanggal akhir cuti tidak boleh sebelum tanggal mulai.")

        # Cegah permohonan dengan tanggal bertabrakan (overlapping) dengan cuti aktif/pending
        if await self.repo.has_overlapping_leave(emp_id, data.start_date, data.end_date):
            raise ValidationError("Anda sudah memiliki permohonan cuti aktif pada rentang tanggal tersebut.")

        # Hitung hari kerja efektif: kecualikan hari Minggu sebagai hari libur mingguan resmi
        total_days = sum(
            1 for i in range((data.end_date - data.start_date).days + 1)
            if (data.start_date + timedelta(days=i)).weekday() != 6
        )
        if total_days <= 0:
            raise ValidationError(
                "Permohonan cuti harus mencakup minimal 1 hari kerja efektif (bukan hari libur saja)."
            )

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
        if user.role not in ALLOWED_REVIEW_ROLES:
            raise ForbiddenError("Hanya PM, HR, OM, atau Super Admin yang berwenang meninjau permohonan cuti.")

        if user.employee_id is None:
            raise ForbiddenError("Akun peninjau cuti wajib tertaut ke data karyawan.")

        leave = await self.repo.get_leave(leave_id)
        if leave is None:
            raise NotFoundError("Permohonan cuti")

        if str(user.employee_id) == str(leave.employee_id):
            raise ForbiddenError("Pemohon cuti tidak dapat menyetujui atau menolak permohonannya sendiri.")

        if leave.status in ("APPROVED_BY_HR", "REJECTED", "CANCELLED"):
            raise AppError("ALREADY_DECIDED", "Permohonan cuti ini sudah diputuskan.", status=409)

        is_pm = user.role == "PROJECT_MANAGER"
        if is_pm and leave.status == "APPROVED_BY_PM":
            raise AppError(
                "ALREADY_APPROVED_BY_PM",
                "Permohonan cuti ini sudah disetujui PM dan menunggu persetujuan HR.",
                status=409,
            )

        new_status = "REJECTED" if data.decision == "REJECTED" else ("APPROVED_BY_PM" if is_pm else "APPROVED_BY_HR")

        await self.repo.update_review(
            leave_id=leave_id,
            status=new_status,
            reviewer_id=user.employee_id,
            is_pm=is_pm,
            note=data.note.strip() if data.note else None,
        )

        # Potong kuota cuti tahunan hanya saat disetujui pertama kali (mencegah double deduction)
        # Serta kembalikan saldo (refund) jika persetujuan awal PM kemudian ditolak oleh HR
        if leave.leave_type == "ANNUAL":
            if data.decision == "APPROVED" and leave.status == "PENDING":
                # Pemotongan pertama kali (baik oleh PM maupun langsung oleh HR)
                await self.repo.deduct_balance(leave.employee_id, leave.start_date.year, leave.total_days)
            elif data.decision == "REJECTED" and leave.status == "APPROVED_BY_PM":
                # Pengembalian kuota karena sebelumnya sudah dipotong saat disetujui PM
                await self.repo.deduct_balance(leave.employee_id, leave.start_date.year, -leave.total_days)

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
