"""Perakitan service modul job_positions (satu permintaan = satu transaksi)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.job_positions.repositories.job_position_repository import JobPositionRepository
from app.modules.job_positions.services.job_position_service import JobPositionService


def get_job_position_service(db: AsyncSession = Depends(get_db_with_user)) -> JobPositionService:
    return JobPositionService(JobPositionRepository(db))
