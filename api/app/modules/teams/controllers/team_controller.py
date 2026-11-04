"""
app/modules/teams/controllers/team_controller.py
Controller orkestrasi use case tim operasional dan keanggotaan.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.teams.dependencies import get_team_logo_service, get_team_service
from app.modules.teams.schemas.team_schema import (
    TEAM_LOGO_PATH,
    AvailableMemberOut,
    MemberAdd,
    TeamAvailabilityItem,
    TeamCreate,
    TeamDetail,
    TeamListItem,
    TeamLogoOut,
    TeamUpdate,
)
from app.modules.teams.services.team_logo_service import TeamLogoService
from app.modules.teams.services.team_service import TeamService


class TeamController:
    """Controller pengelolaan tim kerja dan anggota tim."""

    def __init__(
        self,
        team_service: TeamService = Depends(get_team_service),
        logo_service: TeamLogoService = Depends(get_team_logo_service),
    ) -> None:
        self.service = team_service
        self.logo_service = logo_service

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

    async def handle_set_logo(self, current_user: CurrentUser, team_id: UUID, raw: bytes) -> TeamLogoOut:
        file_id = await self.logo_service.set_logo(current_user, team_id, raw)
        return TeamLogoOut(team_id=team_id, logo_file_id=UUID(file_id),
                           logo_url=TEAM_LOGO_PATH.format(team_id=team_id))

    async def handle_delete_logo(self, current_user: CurrentUser, team_id: UUID) -> None:
        await self.logo_service.delete_logo(current_user, team_id)

    async def handle_get_logo(self, current_user: CurrentUser, team_id: UUID) -> tuple[bytes, str]:
        return await self.logo_service.get_logo(current_user, team_id)

    async def handle_list_available_members(
        self,
        current_user: CurrentUser,
        division_id: UUID,
    ) -> list[AvailableMemberOut]:
        rows = await self.service.list_available_members(current_user, division_id)
        return [AvailableMemberOut(**dict(r._mapping)) for r in rows]

    async def handle_get_teams_availability(
        self,
        current_user: CurrentUser,
        target_date: date,
        division_id: UUID | None = None,
    ) -> list[TeamAvailabilityItem]:
        rows = await self.service.get_teams_availability(current_user, target_date, division_id)
        return [TeamAvailabilityItem(**r) for r in rows]
