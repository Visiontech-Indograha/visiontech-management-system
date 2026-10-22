"""
app/modules/overtime/dependencies.py

Perakitan service modul overtime untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.overtime.services.overtime_service import OvertimeService


def get_overtime_service(db: AsyncSession = Depends(get_db_with_user)) -> OvertimeService:
    return OvertimeService(db)
