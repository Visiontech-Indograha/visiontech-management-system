"""
app/modules/units/dependencies.py

Perakitan service modul units untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.units.repositories.unit_repository import CRUDUnit
from app.modules.units.services.unit_service import UnitService


def get_unit_service(db: AsyncSession = Depends(get_db_with_user)) -> UnitService:
    return UnitService(CRUDUnit(db))
