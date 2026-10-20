"""
app/modules/assets/dependencies.py
Perakitan service modul assets untuk FastAPI `Depends`.
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.assets.repositories.asset_repository import AssetRepository
from app.modules.assets.services.asset_service import AssetService


def get_asset_service(db: AsyncSession = Depends(get_db_with_user)) -> AssetService:
    return AssetService(AssetRepository(db))
