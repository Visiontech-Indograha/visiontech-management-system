"""
app/services/employee_service.py
Karyawan — padanan `domain.js` OFFBOARD dan RESTORE_EMPLOYEE (V-29), plus hapus karyawan (keputusan pemilik
2026-09-25; prototipe tidak punya tindakannya). Izin HR (`manage:users`) dijaga router.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, ValidationError
from app.repositories.employee_repo import EmployeeRepo
from app.repositories.org_clock_repo import OrgClockRepo

RESTORED = "Data dipulihkan sebagai nonaktif. Akses lama tetap dicabut."
ARCHIVED = "Karyawan dihapus. Data historis tetap tersimpan."
OFFBOARDED = "Masa kerja diakhiri dan akses dicabut. Data historis tetap tersedia."


class EmployeeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EmployeeRepo(db)

    async def restore_employee(self, employee_id: UUID, org_id: str) -> dict[str, Any]:
        employee = await self.repo.lock(employee_id, org_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if not employee.deleted:
            raise AppError("INVALID_STATE",
                           "Karyawan tidak dihapus. Untuk bergabung kembali dibutuhkan masa kerja dan akses baru.",
                           status=409)
        await self.repo.restore(employee_id)
        return {"id": str(employee_id), "is_active": False, "message": RESTORED}

    async def archive_employee(self, employee_id: UUID, org_id: str) -> dict[str, Any]:
        """Hanya karyawan yang sudah di-offboard (nonaktif); data historis tidak dihapus."""
        employee = await self.repo.lock(employee_id, org_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if employee.deleted:
            raise AppError("INVALID_STATE", "Karyawan sudah dihapus.", status=409)
        if employee.is_active:
            raise AppError("INVALID_STATE", "Nonaktifkan (offboard) karyawan terlebih dahulu.", status=409)
        await self.repo.archive(employee_id)
        return {"id": str(employee_id), "message": ARCHIVED}

    async def offboard(self, employee_id: UUID, org_id: str, reason: str) -> dict[str, Any]:
        """domain.js OFFBOARD — urutan & pesan sama dengan prototipe."""
        employee = await self.repo.lock(employee_id, org_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if employee.deleted or not employee.is_active:
            raise AppError("INVALID_STATE", "Karyawan sudah nonaktif atau tidak ditemukan.", status=409)
        if not reason.strip():
            raise ValidationError("Alasan offboarding wajib diisi.")
        if await self.repo.on_running_plan(employee_id):
            raise AppError("INVALID_STATE", "Selesaikan atau serahterimakan penugasan aktif sebelum offboarding.",
                           status=409)
        today = (await OrgClockRepo(self.db).local_now(org_id)).today
        await self.repo.offboard(employee_id, reason.strip(), today)
        return {"id": str(employee_id), "message": OFFBOARDED}
