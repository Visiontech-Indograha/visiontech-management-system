"""
app/modules/system_backup/services/backup_service.py
Service logika bisnis untuk registrasi dan pemantauan cadangan sistem.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.system_backup.repositories.backup_repository import BackupRepository
from app.modules.system_backup.schemas.backup_schema import BackupCreate


class BackupService:
    """Service use case registry backup sistem."""

    def __init__(self, db: AsyncSession) -> None:
        self.repo = BackupRepository(db)

    async def list_backups(self, limit: int = 50) -> Sequence[Any]:
        return await self.repo.list_backups(limit)

    async def get_by_id(self, backup_id: UUID) -> Any:
        record = await self.repo.get_by_id(backup_id)
        if not record:
            raise NotFoundError("Data backup tidak ditemukan.")
        return record

    async def record_backup(self, data: BackupCreate) -> Any:
        return await self.repo.record_backup(data)
