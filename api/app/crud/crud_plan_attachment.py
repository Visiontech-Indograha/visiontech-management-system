"""
app/crud/crud_plan_attachment.py
Lampiran rencana kerja mingguan Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDPlanAttachment(CRUDBase):
    """
    Kelas CRUD untuk mengelola data lampiran/berkas (attachment) Master Schema V2.
    """

    async def list_for_plan(self, plan_id: UUID | str) -> list[Any]:
        """Mendapatkan daftar lampiran dari sebuah Work Plan."""
        return []

    async def replace(self, plan_id: UUID | str, file_ids: list[UUID]) -> None:
        """Ganti seluruh lampiran."""
