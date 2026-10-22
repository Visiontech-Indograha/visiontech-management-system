"""
app/modules/work_types/dependencies.py

Perakitan service modul work_types untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.work_types.services.work_type_service import WorkTypeService


def get_work_type_service(db: AsyncSession = Depends(get_db_with_user)) -> WorkTypeService:
    return WorkTypeService(db)
