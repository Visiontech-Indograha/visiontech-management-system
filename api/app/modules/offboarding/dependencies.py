"""
app/modules/offboarding/dependencies.py

Perakitan service modul offboarding. Pengembalian aset lewat API publik modul assets (sesi yang sama = satu transaksi).
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.assets.dependencies import get_asset_service
from app.modules.assets.services.asset_service import AssetService
from app.modules.offboarding.repositories.offboarding_repository import OffboardingRepository
from app.modules.offboarding.services.offboarding_service import OffboardingService


def get_offboarding_service(
    db: AsyncSession = Depends(get_db_with_user),
    assets: AssetService = Depends(get_asset_service),
) -> OffboardingService:
    return OffboardingService(OffboardingRepository(db), assets)
