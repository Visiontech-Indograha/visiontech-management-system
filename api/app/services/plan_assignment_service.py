"""Aturan pembuat dan cakupan personel SK (R-23)."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any
from uuid import UUID

from app.api.deps import CurrentUser
from app.core.errors import AppError, ForbiddenError
from app.core.permissions import RoleCode
from app.repositories.plan_assignment_repo import PlanAssignmentRepo


class PlanAssignmentService:
    def __init__(self, repo: PlanAssignmentRepo) -> None:
        self.repo = repo

    @staticmethod
    def _oversees(user: CurrentUser) -> bool:
        return RoleCode.ADMIN in user.roles or RoleCode.OPS in user.roles

    async def validate_owner(self, user: CurrentUser, unit_id: UUID, pm_employee_id: UUID) -> None:
        """PM membuat untuk dirinya/unitnya; OPS (OM) dan ADMIN boleh memilih PM."""
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
    ) -> None:
        """OPS/ADMIN bebas lintas unit; PM hanya dapat memilih karyawan pada unit SK-nya."""
        if self._oversees(user):
            return
        ids = [str(value) for value in employee_ids]
        units = await self.repo.employee_units(ids, user.organization_id)
        if any(units.get(employee_id) != str(plan_unit_id) for employee_id in ids):
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

