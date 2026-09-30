"""
app/services/plan_member_service.py
Aturan susunan tim SK draft — padanan `checkMembers`/`checkSchedule` di prototype/js/domain.js.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.api.deps import CurrentUser
from app.core.enums import PlanStatus
from app.core.errors import AppError, ConflictError, NotFoundError
from app.crud.crud_plan_assignment import CRUDPlanAssignment
from app.crud.crud_plan_member import CRUDPlanMember
from app.services.plan_assignment_service import PlanAssignmentService


@dataclass(frozen=True)
class Team:
    leader_employee_id: str | None
    member_employee_ids: list[str]
    row_version: int


class PlanMemberService:
    def __init__(self, repo: CRUDPlanMember) -> None:
        self.repo = repo

    async def team(self, plan_id: UUID) -> list[Any]:
        """Tim aktif untuk detail SK — akses VIEW sudah diperiksa penjaga rute."""
        return await self.repo.active_team(plan_id)

    async def set_team(
        self,
        user: CurrentUser,
        plan_id: UUID,
        leader_id: UUID | None,
        member_ids: list[UUID],
        row_version: int,
    ) -> Team:
        plan = await self.repo.lock_plan(plan_id, user.organization_id)
        if plan is None:
            raise NotFoundError("SK")
        if plan.status != PlanStatus.DRAFT:
            raise AppError(
                "PLAN_NOT_DRAFT",
                "Susunan tim hanya dapat diubah selama SK masih draf. Untuk SK yang sudah terbit, gunakan adendum personel.",
                status=409,
            )
        if plan.row_version != row_version:
            raise ConflictError()

        leader = str(leader_id) if leader_id else None
        members = list(dict.fromkeys(str(m) for m in member_ids))  # buang duplikat, urutan tetap
        if leader and leader in members:
            raise AppError("VALIDATION_ERROR", "Ketua tim tidak boleh sekaligus tercatat sebagai anggota.", status=422)
        if leader and plan.pm_employee_id and leader == str(plan.pm_employee_id):
            raise AppError("VALIDATION_ERROR", "Ketua tim tidak boleh sama dengan PM pekerjaan ini.", status=422)

        people = ([leader] if leader else []) + members
        known = await self.repo.active_employees(people, user.organization_id)
        if set(people) - known:
            raise NotFoundError("Karyawan")
        current = [m.employee_id for m in await self.repo.active_team(plan_id)]
        await PlanAssignmentService(CRUDPlanAssignment(self.repo.db)).validate_team_scope(
            user, plan.unit_id, people, current_team=current)

        conflicts = await self.repo.schedule_conflicts(people, plan_id)
        if conflicts:
            numbers = ", ".join(sorted({c.number or c.title for c in conflicts}))
            raise AppError(
                "PERSONNEL_CONFLICT",
                f"Jadwal personel bertabrakan dengan pekerjaan lain: {numbers}.",
                status=409,
                details={"conflicts": [
                    {"employee_id": c.employee_id, "work_plan_id": c.work_plan_id, "number": c.number, "title": c.title}
                    for c in conflicts
                ]},
            )

        await self.repo.replace_team(plan_id, plan.period_start, leader, members)
        new_version = await self.repo.set_leader(plan_id, leader)
        return Team(leader_employee_id=leader, member_employee_ids=members, row_version=new_version)
