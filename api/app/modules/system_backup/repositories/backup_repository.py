"""
app/modules/system_backup/repositories/backup_repository.py
Repository akses basis data untuk tabel system_backup_registry.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase
from app.modules.system_backup.schemas.backup_schema import BackupCreate


class BackupRepository(CRUDBase):
    """Akses query untuk data registry backup sistem."""

    async def list_backups(self, limit: int = 50) -> Sequence[Any]:
        sql = """
            SELECT
                backup_id,
                backup_cycle,
                period_start,
                period_end,
                file_path_url,
                compressed_size_mb,
                sha256_checksum,
                status,
                created_at
            FROM system_backup_registry
            ORDER BY created_at DESC
            LIMIT :limit
        """
        return await self.fetchall(sql, {"limit": limit})

    async def get_by_id(self, backup_id: UUID) -> Any | None:
        sql = """
            SELECT
                backup_id,
                backup_cycle,
                period_start,
                period_end,
                file_path_url,
                compressed_size_mb,
                sha256_checksum,
                status,
                created_at
            FROM system_backup_registry
            WHERE backup_id = :id
        """
        return await self.fetchone(sql, {"id": backup_id})

    async def record_backup(self, data: BackupCreate) -> Any:
        backup_id = uuid.uuid4()
        sql = """
            INSERT INTO system_backup_registry (
                backup_id, backup_cycle, period_start, period_end,
                file_path_url, compressed_size_mb, sha256_checksum,
                status, created_at
            ) VALUES (
                :id, :cycle, :start_date, :end_date,
                :url, :size, :hash,
                :status, NOW()
            )
            RETURNING backup_id
        """
        await self.execute(sql, {
            "id": backup_id,
            "cycle": data.backup_cycle,
            "start_date": data.period_start,
            "end_date": data.period_end,
            "url": data.file_path_url,
            "size": data.compressed_size_mb,
            "hash": data.sha256_checksum,
            "status": data.status,
        })
        return await self.get_by_id(backup_id)
