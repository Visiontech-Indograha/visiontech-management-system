"""
app/services/employee_service.py
Karyawan (V-29) — padanan `domain.js` RESTORE_EMPLOYEE, plus hapus karyawan (keputusan pemilik
2026-09-25; prototipe tidak punya tindakannya). Izin HR (`manage:users`) dijaga router.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.repositories.employee_repo import EmployeeRepo

RESTORED = "Data dipulihkan sebagai nonaktif. Akses lama tetap dicabut."
ARCHIVED = "Karyawan dihapus. Data historis tetap tersimpan."


class EmployeeService:
    def __init__(self, db: AsyncSession) -> None:
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
