"""
app/modules/teams/dependencies.py

Perakitan service modul teams untuk FastAPI `Depends`.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.teams.repositories.team_repository import TeamRepository
from app.modules.teams.services.team_service import TeamService


def get_team_service(db: AsyncSession = Depends(get_db_with_user)) -> TeamService:
    return TeamService(TeamRepository(db))
