"""
app/modules/teams/services/team_service.py
Service logika bisnis untuk manajemen tim kerja lapangan dan anggota tim.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.core.errors import NotFoundError
from app.modules.teams.repositories.team_repository import TeamRepository
from app.modules.teams.schemas.team_schema import TeamCreate, TeamUpdate


class TeamService:
    """Service use case tim dan anggota."""

    def __init__(self, db: AsyncSession = Depends(get_db_with_user)) -> None:
        self.repo = TeamRepository(db)

    async def list_teams(self, division_id: UUID | None = None) -> Sequence[Any]:
        return await self.repo.list_teams(division_id)

    async def get_team(self, team_id: UUID) -> Any:
        team = await self.repo.get_team_by_id(team_id)
        if not team:
            raise NotFoundError("Tim tidak ditemukan.")
        members = await self.repo.list_team_members(team_id)
        data = dict(team._mapping)
        data["members"] = [dict(m._mapping) for m in members]
        return data

    async def create_team(self, data: TeamCreate) -> Any:
        return await self.repo.create_team(data)

    async def update_team(self, team_id: UUID, data: TeamUpdate) -> Any:
        team = await self.repo.update_team(team_id, data)
        if not team:
            raise NotFoundError("Tim tidak ditemukan.")
        return team

    async def delete_team(self, team_id: UUID) -> None:
        await self.repo.delete_team(team_id)

    async def add_member(self, team_id: UUID, employee_id: UUID) -> Any:
        team = await self.repo.get_team_by_id(team_id)
        if not team:
            raise NotFoundError("Tim tidak ditemukan.")
        return await self.repo.add_member(team_id, employee_id)

    async def remove_member(self, team_id: UUID, employee_id: UUID) -> None:
        team = await self.repo.get_team_by_id(team_id)
        if not team:
            raise NotFoundError("Tim tidak ditemukan.")
        await self.repo.remove_member(team_id, employee_id)
