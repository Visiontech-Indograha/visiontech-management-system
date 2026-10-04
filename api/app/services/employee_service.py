"""
app/services/employee_service.py
Karyawan — padanan `domain.js` OFFBOARD dan RESTORE_EMPLOYEE (V-29), plus hapus karyawan (keputusan pemilik
2026-09-25; prototipe tidak punya tindakannya). Izin HR (`manage:users`) dijaga router.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.permissions import Permission
from app.crud.crud_employee import CRUDEmployee
from app.crud.crud_org_clock import CRUDOrgClock

RESTORED = "Data dipulihkan sebagai nonaktif. Akses lama tetap dicabut."
ARCHIVED = "Karyawan dihapus. Data historis tetap tersimpan."
OFFBOARDED = "Masa kerja diakhiri dan akses dicabut. Data historis tetap tersedia."


class EmployeeService:
    """Layanan untuk mengelola data karyawan, penempatan (assignment), mutasi, dan offboarding."""
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDEmployee(db)

    async def private_viewer(self, user_id: str, permissions: list[str]) -> tuple[bool, str | None]:
        """Prototipe `privateAccess`: data kontak pribadi hanya untuk HR (dan admin) serta pemiliknya.
        Hasil: (boleh melihat semua, employee_id milik pengguna)."""
        if Permission.MANAGE_EMPLOYEE_DOCUMENTS.value in permissions:
            return True, None
        own = await self.repo.employee_of_user(user_id)
        return False, str(own) if own else None

    async def restore_employee(self, employee_id: UUID, org_id: str) -> dict[str, Any]:
        """
        Memulihkan karyawan yang dihapus (deleted).
        Karyawan yang dipulihkan berstatus nonaktif dan harus diberikan akses baru.
        """
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

    async def assignments(self, employee_id: UUID, org_id: str) -> list[Any]:
        """
        Mendapatkan riwayat penempatan (jabatan dan unit) seorang karyawan.
        """
        rows = await self.repo.assignments(employee_id, org_id)
        if rows is None:
            raise NotFoundError("Karyawan")
        return rows

    async def promote(self, employee_id: UUID, org_id: str, position: str, unit_id: UUID | None,
                      valid_from: date) -> Any:
        """
        domain.js PROMOTE — mutasi atau promosi jabatan karyawan.
        karyawan aktif, jabatan & unit valid, mutasi lintas unit diblokir selama
        masih bertugas di SK aktif. Unit kosong = tetap di unit sekarang.
        """
        employee = await self.repo.lock(employee_id, org_id)
        if employee is None or employee.deleted:
            raise NotFoundError("Karyawan")
        if not employee.is_active:
            raise AppError("INVALID_STATE", "Karyawan harus aktif.", status=409)
        if not position.strip():
            raise ValidationError("Jabatan dan unit wajib valid.")
            
        target_unit = str(unit_id) if unit_id else employee.unit_id
        # Aturan bisnis: Tidak boleh memutasi karyawan ke unit lain jika ia masih bagian dari tim SK di unit lamanya yang belum selesai.
        if target_unit != employee.unit_id and await self.repo.on_running_plan(employee_id):
            raise AppError("INVALID_STATE", "Mutasi lintas unit diblokir sampai penugasan aktif diserahterimakan.",
                           status=409)
                           
        last_start = await self.repo.last_assignment_start(employee_id)
        # Menjaga urutan kronologis penempatan.
        if last_start is not None and valid_from < last_start:
            raise ValidationError("Tanggal berlaku tidak boleh sebelum penempatan terakhir.")
            
        return await self.repo.promote(employee_id, position.strip(), target_unit, valid_from)

    async def offboard(self, employee_id: UUID, org_id: str, reason: str) -> dict[str, Any]:
        """
        domain.js OFFBOARD — menghentikan masa kerja karyawan (PHK, Resign).
        urutan & pesan sama dengan prototipe.
        """
        employee = await self.repo.lock(employee_id, org_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if employee.deleted or not employee.is_active:
            raise AppError("INVALID_STATE", "Karyawan sudah nonaktif atau tidak ditemukan.", status=409)
        if not reason.strip():
            raise ValidationError("Alasan offboarding wajib diisi.")
            
        # Aturan bisnis: Karyawan yang masih tergabung dalam pekerjaan berjalan (SK aktif) tidak bisa diberhentikan.
        if await self.repo.on_running_plan(employee_id):
            raise AppError("INVALID_STATE", "Selesaikan atau serahterimakan penugasan aktif sebelum offboarding.",
                           status=409)
                           
        today = (await CRUDOrgClock(self.db).local_now(org_id)).today
        await self.repo.offboard(employee_id, reason.strip(), today)
        return {"id": str(employee_id), "message": OFFBOARDED}
