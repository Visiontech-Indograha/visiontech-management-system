"""
app/services/file_service.py
Pencatatan & otorisasi berkas. Pengunggahan objek ke MinIO tetap di router (`app.core.storage`).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.security import CurrentUser
from app.crud.crud_file import CRUDFile
from app.shared.access.access_service import check_file_access


class FileService:
    """Metadata `file_object`: deduplikasi, pencatatan, dan siapa boleh membuka berkas (V-17)."""

    def __init__(self, repo: CRUDFile) -> None:
        self.repo = repo

    async def duplicate_of(self, org_id: UUID | str, sha256: bytes) -> Any:
        """Berkas yang isinya sama di organisasi ini, atau None."""
        return await self.repo.find_by_hash(org_id, sha256)

    async def register(
        self,
        user: CurrentUser,
        *,
        file_id: str,
        storage_key: str,
        file_name: str | None,
        mime_type: str,
        byte_size: int,
        sha256: bytes,
    ) -> str:
        """Catat berkas baru milik organisasi pengguna → id berkas tersimpan (berbeda dari `file_id` bila berkas
        yang sama baru saja dicatat unggahan lain)."""
        return await self.repo.insert(
            file_id=file_id,
            org_id=user.organization_id,
            storage_key=storage_key,
            file_name=file_name,
            mime_type=mime_type,
            byte_size=byte_size,
            sha256=sha256,
            user_id=user.user_id,
        )

    async def authorize(self, file_id: UUID, user: CurrentUser) -> Any:
        """Berkas yang boleh dibuka pengguna; selain itu NotFoundError (404, bukan 403)."""
        return await check_file_access(self.repo.db, file_id, user)
