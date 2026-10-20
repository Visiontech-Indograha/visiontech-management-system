"""
app/modules/offboarding/dependencies.py

Perakitan service modul offboarding untuk FastAPI `Depends`.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.offboarding.services.offboarding_service import OffboardingService


def get_offboarding_service(db: AsyncSession = Depends(get_db_with_user)) -> OffboardingService:
    return OffboardingService(db)
