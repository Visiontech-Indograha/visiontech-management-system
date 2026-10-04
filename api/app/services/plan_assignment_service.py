"""Aturan pembuat dan cakupan personel SK (R-23)."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any
from uuid import UUID

from app.core.errors import AppError, ForbiddenError
from app.core.permissions import RoleCode
from app.core.security import CurrentUser
from app.crud.crud_plan_assignment import CRUDPlanAssignment


class PlanAssignmentService:
    """Layanan validasi pemilihan personel (PM, ketua, anggota) pada pembentukan SK."""
    def __init__(self, repo: CRUDPlanAssignment) -> None:
        self.repo = repo

    @staticmethod
    def _oversees(user: CurrentUser) -> bool:
        """Mengecek apakah pengguna adalah admin atau tim OPS yang memiliki akses lintas unit."""
        return RoleCode.ADMIN in user.roles or RoleCode.OPS in user.roles

    async def validate_owner(self, user: CurrentUser, unit_id: UUID, pm_employee_id: UUID) -> None:
        """
        Memastikan PM yang ditunjuk valid dan sesuai dengan kewenangan pembuat SK.
        PM membuat untuk dirinya/unitnya; OPS (OM) dan ADMIN boleh memilih PM.
        
        Args:
            user: Informasi pengguna pembuat SK.
            unit_id: ID unit pelaksanaan SK.
            pm_employee_id: ID karyawan yang akan menjadi PM.
            
        Raises:
            ForbiddenError: Jika pembuat bukan karyawan aktif.
            AppError: Jika PM tidak berada pada unit yang dipilih, atau mencoba membuat untuk PM lain tanpa akses OPS/ADMIN.
        """
        creator = await self.repo.employee_of_user(user.user_id)
        if creator is None:
            raise ForbiddenError("Akun Anda belum tertaut ke data karyawan aktif.")
        pm_units = await self.repo.employee_units([pm_employee_id], user.organization_id)
        if pm_units.get(str(pm_employee_id)) != str(unit_id):
            raise AppError(
                "PLAN_PM_UNIT_MISMATCH",
                "PM pekerjaan harus merupakan karyawan aktif pada unit SK yang dipilih.",
                status=422,
            )
        if not self._oversees(user) and str(pm_employee_id) != str(creator.employee_id):
            raise AppError(
                "PLAN_PM_MUST_BE_SELF",
                "Saat PM membuat SK, PM pekerjaan otomatis adalah dirinya sendiri.",
                status=422,
            )

    async def validate_team_scope(
        self,
        user: CurrentUser,
        plan_unit_id: UUID | str,
        employee_ids: Iterable[UUID | str],
        current_team: Iterable[UUID | str] = (),
    ) -> None:
        """
        Memvalidasi personel tim di lapangan (ketua dan anggota).
        Seluruh tim wajib staf lapangan (R-26). OPS/ADMIN bebas lintas unit; PM hanya dapat
        MENAMBAHKAN karyawan unit SK-nya: anggota yang sudah ada di tim (`current_team`, mis. pilihan
        OPS lintas unit) tidak diperiksa ulang cakupan unitnya (docs/10 Bagian C, R-26).
        
        Args:
            user: Pengguna yang melakukan validasi.
            plan_unit_id: ID unit pelaksana SK.
            employee_ids: Kumpulan ID karyawan anggota/ketua.
            current_team: Kumpulan ID anggota saat ini, untuk mengizinkan perubahan campuran lintas unit.
            
        Raises:
            AppError: Jika personel bukan staf lapangan atau di luar kewenangan unit PM.
        """
        ids = [str(value) for value in employee_ids]
        eligible = await self.repo.eligible_field_staff(ids, user.organization_id)
        if set(ids) - eligible:
            raise AppError(
                "PERSONNEL_NOT_FIELD_STAFF",
                "Ketua dan anggota tim hanya dapat dipilih dari staf lapangan dengan akun aktif.",
                status=422,
            )
        if self._oversees(user):
            return
        added = [employee_id for employee_id in ids if employee_id not in {str(v) for v in current_team}]
        units = await self.repo.employee_units(added, user.organization_id)
        if any(units.get(employee_id) != str(plan_unit_id) for employee_id in added):
            raise AppError(
                "PERSONNEL_OUTSIDE_PM_UNIT",
                "PM hanya dapat memilih ketua dan anggota dari unitnya sendiri.",
                status=422,
            )

    async def options(self, user: CurrentUser, period_start: date, period_end: date) -> dict[str, Any]:
        if period_end < period_start:
            raise AppError("VALIDATION_ERROR", "Tanggal selesai tidak boleh sebelum tanggal mulai.", status=422)
        creator = await self.repo.employee_of_user(user.user_id)
        if creator is None:
            raise ForbiddenError("Akun Anda belum tertaut ke data karyawan aktif.")
        oversees = self._oversees(user)
        personnel = await self.repo.available_personnel(
            user.organization_id,
            period_start,
            period_end,
            None if oversees else creator.unit_id,
        )
        managers = await self.repo.active_project_managers(user.organization_id) if oversees else []
        return {
            "can_choose_pm": oversees,
            "fixed_pm_employee_id": None if oversees else creator.employee_id,
            "fixed_unit_id": None if oversees else creator.unit_id,
            "pm_options": managers,
            "personnel_options": personnel,
        }

