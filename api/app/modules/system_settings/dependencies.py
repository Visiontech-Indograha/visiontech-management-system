"""Perakitan service setelan sistem untuk FastAPI `Depends` (satu permintaan = satu transaksi)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.system_settings.repositories.system_settings_repository import SystemSettingsRepository
from app.modules.system_settings.services.system_settings_service import SystemSettingsService


def get_system_settings_service(db: AsyncSession = Depends(get_db_with_user)) -> SystemSettingsService:
    return SystemSettingsService(SystemSettingsRepository(db))
