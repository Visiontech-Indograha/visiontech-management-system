"""
app/modules/offices/dependencies.py

Perakitan service modul offices untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.offices.repositories.office_repository import CRUDOffice
from app.modules.offices.services.office_service import OfficeService


def get_office_service(db: AsyncSession = Depends(get_db_with_user)) -> OfficeService:
    return OfficeService(CRUDOffice(db))
