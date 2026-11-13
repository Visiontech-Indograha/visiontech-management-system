"""Perakitan service penerima push (satu permintaan = satu transaksi)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_db_with_user
from app.modules.hikvision.repositories.hikvision_admin_repository import HikvisionAdminRepository
from app.modules.hikvision.repositories.hikvision_repository import HikvisionRepository
from app.modules.hikvision.services.hikvision_admin_service import HikvisionAdminService
from app.modules.hikvision.services.penerima_service import PenerimaService


def get_penerima_service(db: AsyncSession = Depends(get_db)) -> PenerimaService:
    return PenerimaService(HikvisionRepository(db))


def get_admin_service(db: AsyncSession = Depends(get_db_with_user)) -> HikvisionAdminService:
    return HikvisionAdminService(HikvisionAdminRepository(db), db)
