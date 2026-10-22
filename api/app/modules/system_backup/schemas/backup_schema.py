"""
app/modules/system_backup/schemas/backup_schema.py
Skema data Pydantic untuk System Backup Registry.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BackupCreate(BaseModel):
    backup_cycle: str = Field(..., description="'DAILY', 'WEEKLY', 'MONTHLY'")
    period_start: date
    period_end: date
    file_path_url: str
    compressed_size_mb: Decimal
    sha256_checksum: str = Field(..., min_length=64, max_length=64)
    status: str = "SUCCESS"


class BackupOut(BaseModel):
    backup_id: UUID
    backup_cycle: str
    period_start: date
    period_end: date
    file_path_url: str
    compressed_size_mb: Decimal
    sha256_checksum: str
    status: str
    created_at: datetime
