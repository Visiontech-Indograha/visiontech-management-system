"""
app/modules/system_backup/controllers/backup_controller.py
Controller orkestrasi use case registrasi dan pemantauan cadangan basis data.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.system_backup.schemas.backup_schema import BackupCreate, BackupOut
from app.modules.system_backup.services.backup_service import BackupService


class BackupController:
    """Controller pengelolaan registry backup sistem (Super Admin)."""

    def __init__(self, service: BackupService = Depends()) -> None:
        self.service = service

    async def handle_list_backups(
        self,
        current_user: CurrentUser,
        limit: int = 50,
    ) -> list[BackupOut]:
        rows = await self.service.list_backups(limit)
        return [BackupOut(**dict(r._mapping)) for r in rows]

    async def handle_get_by_id(
        self,
        current_user: CurrentUser,
        backup_id: UUID,
    ) -> BackupOut:
        row = await self.service.get_by_id(backup_id)
        return BackupOut(**dict(row._mapping))

    async def handle_record_backup(
        self,
        current_user: CurrentUser,
        data: BackupCreate,
    ) -> BackupOut:
        row = await self.service.record_backup(data)
        return BackupOut(**dict(row._mapping))
