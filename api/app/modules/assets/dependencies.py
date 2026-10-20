"""
app/modules/assets/dependencies.py

Perakitan service modul assets untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.assets.services.asset_service import AssetReservationService


def get_asset_reservation_service(db: AsyncSession = Depends(get_db_with_user)) -> AssetReservationService:
    return AssetReservationService(db)
