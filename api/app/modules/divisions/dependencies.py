"""
app/modules/divisions/dependencies.py

Perakitan service modul divisions untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.divisions.repositories.division_repository import CRUDDivision
from app.modules.divisions.services.division_service import DivisionService


def get_division_service(db: AsyncSession = Depends(get_db_with_user)) -> DivisionService:
    return DivisionService(CRUDDivision(db))
