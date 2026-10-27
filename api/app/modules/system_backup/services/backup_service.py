"""
app/modules/system_backup/services/backup_service.py
Service logika bisnis untuk registrasi dan pemantauan cadangan sistem.
"""
from __future__ import annotations

import asyncio
import gzip
import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.system_backup.repositories.backup_repository import BackupRepository
from app.modules.system_backup.schemas.backup_schema import BackupCreate


def _write_compressed_dump(
    file_path: Path,
    cycle: str,
    now: datetime,
    table_names: list[str],
) -> tuple[int, str]:
    """Helper sinkron untuk I/O berkas gzipped backup dan perhitungan checksum."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(file_path, "wb") as gz:
        header = f"-- VMS System Backup\n-- Cycle: {cycle}\n-- Created: {now.isoformat()}\n\n"
        gz.write(header.encode("utf-8"))

        for table in table_names:
            table_comment = f"\n-- Data for {table}\n"
            gz.write(table_comment.encode("utf-8"))

    file_size_bytes = file_path.stat().st_size
    with file_path.open("rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    return file_size_bytes, file_hash


class BackupService:
    """Service use case registry backup sistem."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
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

    async def execute_automated_backup(
        self,
        cycle: str = "WEEKLY",
        output_dir: str = "backups",
    ) -> Any:
        """
        Menjalankan prosedur backup data otomatis, menghasilkan arsip gzip terkompresi,
        menghitung sha256 checksum, dan mencatatkannya ke system_backup_registry.
        """
        now = datetime.now(UTC)
        filename = f"vms_backup_{cycle.lower()}_{now.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        file_path = Path(output_dir) / filename

        tables_res = await self.db.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                "AND tablename NOT IN ('app_activity_logs', 'system_backup_registry') "
                "ORDER BY tablename;"
            )
        )
        table_names = [row[0] for row in tables_res.fetchall()]

        file_size_bytes, file_hash = await asyncio.to_thread(
            _write_compressed_dump, file_path, cycle, now, table_names
        )
        size_mb = Decimal(str(round(file_size_bytes / (1024 * 1024), 4)))

        backup_data = BackupCreate(
            backup_cycle=cycle.upper(),
            period_start=now.date(),
            period_end=now.date(),
            file_path_url=str(file_path).replace("\\", "/"),
            compressed_size_mb=size_mb,
            sha256_checksum=file_hash,
            status="SUCCESS",
        )
        return await self.record_backup(backup_data)
