"""
app/modules/system_backup/dependencies.py

Perakitan service modul system_backup untuk FastAPI `Depends`.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.system_backup.services.backup_service import BackupService


def get_backup_service(db: AsyncSession = Depends(get_db_with_user)) -> BackupService:
    return BackupService(db)
