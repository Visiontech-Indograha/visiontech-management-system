"""
app/modules/mess/dependencies.py

Perakitan service modul mess untuk FastAPI `Depends`.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.mess.services.mess_service import MessService


def get_mess_service(db: AsyncSession = Depends(get_db_with_user)) -> MessService:
    return MessService(db)
