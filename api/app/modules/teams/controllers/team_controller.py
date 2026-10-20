"""
app/modules/teams/controllers/team_controller.py
Controller orkestrasi use case tim operasional dan keanggotaan.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.teams.dependencies import get_team_service
from app.modules.teams.schemas.team_schema import (
    MemberAdd,
    TeamCreate,
    TeamDetail,
    TeamListItem,
    TeamUpdate,
)
from app.modules.teams.services.team_service import TeamService


class TeamController:
    """Controller pengelolaan tim kerja dan anggota tim."""

    def __init__(self, team_service: TeamService = Depends(get_team_service)) -> None:
        self.service = team_service

    async def handle_list_teams(
        self,
        current_user: CurrentUser,
        division_id: UUID | None = None,
    ) -> list[TeamListItem]:
        rows = await self.service.list_teams(current_user, division_id)
        return [TeamListItem(**dict(r._mapping)) for r in rows]

    async def handle_get_team(
        self,
        current_user: CurrentUser,
        team_id: UUID,
    ) -> TeamDetail:
        data = await self.service.get_team(current_user, team_id)
        return TeamDetail(**data)

    async def handle_create_team(
        self,
        current_user: CurrentUser,
        data: TeamCreate,
    ) -> TeamListItem:
        row = await self.service.create_team(current_user, data)
        return TeamListItem(**dict(row._mapping))

    async def handle_update_team(
        self,
        current_user: CurrentUser,
        team_id: UUID,
        data: TeamUpdate,
    ) -> TeamListItem:
        row = await self.service.update_team(current_user, team_id, data)
        return TeamListItem(**dict(row._mapping))

    async def handle_delete_team(
        self,
        current_user: CurrentUser,
        team_id: UUID,
    ) -> dict[str, str]:
        await self.service.delete_team(current_user, team_id)
        return {"message": "Tim berhasil dihapus."}

    async def handle_add_member(
        self,
        current_user: CurrentUser,
        team_id: UUID,
        data: MemberAdd,
    ) -> dict[str, str]:
        await self.service.add_member(current_user, team_id, data.employee_id)
        return {"message": "Anggota berhasil ditambahkan ke tim."}

    async def handle_remove_member(
        self,
        current_user: CurrentUser,
        team_id: UUID,
        employee_id: UUID,
    ) -> dict[str, str]:
        await self.service.remove_member(current_user, team_id, employee_id)
        return {"message": "Anggota berhasil dikeluarkan dari tim."}
