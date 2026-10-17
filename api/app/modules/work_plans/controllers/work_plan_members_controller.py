"""
app/modules/work_plans/controllers/work_plan_members_controller.py

Controller orkestrasi use case susunan tim SK (ketua dan anggota).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.api.deps import get_plan_member_service
from app.modules.work_plans.schemas.work_plan_schema import (
    TeamMemberOut,
    TeamRequest,
    TeamResponse,
)
from app.modules.work_plans.services.work_plan_service import PlanMemberService
from app.services.access_service import PlanAccess


class WorkPlanMembersController:
    """Controller pembacaan dan pembaruan susunan anggota tim rencana kerja."""

    def __init__(
        self,
        plan_member_service: PlanMemberService = Depends(get_plan_member_service),
    ) -> None:
        self.service = plan_member_service

    async def handle_get_team(
        self,
        plan_id: UUID,
    ) -> list[TeamMemberOut]:
        """Mengambil susunan anggota tim kerja aktif pada rencana kerja."""
        rows = await self.service.team(plan_id)
        return [TeamMemberOut(**r._mapping) for r in rows]

    async def handle_set_team(
        self,
        access: PlanAccess,
        plan_id: UUID,
        payload: TeamRequest,
    ) -> TeamResponse:
        """Menyetel atau memperbarui susunan ketua dan anggota tim rencana kerja."""
        team = await self.service.set_team(
            access.user,
            plan_id,
            payload.leader_employee_id,
            payload.member_employee_ids,
            payload.row_version,
        )
        return TeamResponse(
            leader_employee_id=team.leader_employee_id,
            member_employee_ids=team.member_employee_ids,
            row_version=team.row_version,
        )


__all__ = ["WorkPlanMembersController"]
