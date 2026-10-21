"""Perakitan service modul projects (satu permintaan = satu transaksi)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.projects.repositories.project_repository import ProjectRepository
from app.modules.projects.services.project_service import ProjectService


def get_project_service(db: AsyncSession = Depends(get_db_with_user)) -> ProjectService:
    return ProjectService(ProjectRepository(db))
