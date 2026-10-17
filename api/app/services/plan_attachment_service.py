"""
app/services/plan_attachment_service.py
Lampiran draf SK (V-29) — padanan `domain.js` SAVE_ATTACHMENTS: hanya selagi DRAFT, seluruh daftar
diganti. Kewenangan (PM unit/OPS) dijaga penjaga V-07 di router; berkas satu organisasi dicek router.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import ValidationError
from app.crud.crud_plan_attachment import CRUDPlanAttachment
from app.services.access_service import PlanAccess, require_plan_status


class PlanAttachmentService:
    """Layanan pengelolaan lampiran dokumen pada draf SK."""

    def __init__(self, db: AsyncSession) -> None:
        self.repo = CRUDPlanAttachment(db)

    async def list_attachments(self, access: PlanAccess) -> list[Any]:
        """
        Mendaftar seluruh berkas lampiran yang tertaut ke SK.

        Args:
            access (PlanAccess): Objek akses rencana kerja saat ini.

        Returns:
            list[Any]: Daftar lampiran SK.
        """
        return await self.repo.list_for_plan(access.plan.id)

    async def save_attachments(self, access: PlanAccess, file_ids: list[UUID]) -> list[Any]:
        """
        Menyimpan perubahan daftar lampiran, menimpa daftar sebelumnya.
        Hanya dapat dilakukan selama SK berstatus DRAFT.

        Args:
            access (PlanAccess): Objek akses rencana kerja.
            file_ids (list[UUID]): Daftar ID file lampiran baru.

        Returns:
            list[Any]: Daftar lampiran SK yang telah diperbarui.
        """
        require_plan_status(access, PlanStatus.DRAFT)
        if len(set(file_ids)) != len(file_ids):
            raise ValidationError("Ada lampiran yang dipilih lebih dari sekali.")
        await self.repo.replace(access.plan.id, file_ids)
        return await self.repo.list_for_plan(access.plan.id)
