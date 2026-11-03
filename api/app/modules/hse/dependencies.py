"""
api/app/modules/hse/dependencies.py

Dependensi injection untuk service modul HSE.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB_SCOPE, get_db
from app.modules.hse.services.hse_service import HseService


def get_hse_service(db: AsyncSession = Depends(get_db, scope=DB_SCOPE)) -> HseService:
    return HseService(db)
