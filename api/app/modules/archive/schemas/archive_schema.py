"""Skema Arsip: item yang sudah dihapus (soft delete) dan hasil pemulihan."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ArchiveItemOut(BaseModel):
    id: str
    module: str
    name: str
    code: str | None = None
    deleted_at: datetime | None = None
