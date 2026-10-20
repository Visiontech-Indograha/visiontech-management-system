"""
app/modules/hse/dependencies.py

Perakitan service modul hse untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.hse.services.hse_service import HseService


def get_hse_service(db: AsyncSession = Depends(get_db_with_user)) -> HseService:
    return HseService(db)
