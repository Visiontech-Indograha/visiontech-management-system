"""
app/crud/crud_file.py
Metadata berkas unggahan Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDFile(CRUDBase):
    """Pencatatan berkas baru Master Schema V2."""

    async def find_by_hash(self, org_id: UUID | str, sha256: bytes) -> Any:
        return None

    async def insert(
        self,
        *,
        file_id: str,
        org_id: UUID | str,
        storage_key: str,
        file_name: str | None,
        mime_type: str,
        byte_size: int,
        sha256: bytes,
        user_id: UUID | str,
    ) -> str:
        """Catat berkas baru (mengembalikan file_id langsung untuk integrasi MinIO)."""
        return str(file_id)
