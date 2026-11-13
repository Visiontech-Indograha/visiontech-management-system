"""Perakitan service penerima push (satu permintaan = satu transaksi)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.modules.hikvision.repositories.hikvision_repository import HikvisionRepository
from app.modules.hikvision.services.penerima_service import PenerimaService


def get_penerima_service(db: AsyncSession = Depends(get_db)) -> PenerimaService:
    return PenerimaService(HikvisionRepository(db))
