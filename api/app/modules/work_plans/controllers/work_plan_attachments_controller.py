"""
app/modules/work_plans/controllers/work_plan_attachments_controller.py

Controller orkestrasi use case berkas lampiran pendukung draf rencana kerja (SK).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.work_plans.dependencies import get_plan_attachment_service
from app.modules.work_plans.schemas.work_plan_schema import (
    AttachmentResponse,
    AttachmentsRequest,
)
from app.modules.work_plans.services.plan_attachment_service import PlanAttachmentService
from app.shared.access.access_service import PlanAccess, ensure_same_org


def _out(rows: list[Any]) -> list[AttachmentResponse]:
    """Fungsi pembantu memetakan list baris database ke AttachmentResponse."""
    return [AttachmentResponse(**row._mapping) for row in rows]


class WorkPlanAttachmentsController:
    """Controller pengelolaan lampiran dokumen rencana kerja."""

    def __init__(
        self,
        plan_attachment_service: PlanAttachmentService = Depends(get_plan_attachment_service),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> None:
        self.service = plan_attachment_service
        self.db = db

    async def handle_list_attachments(
        self,
        access: PlanAccess,
    ) -> list[AttachmentResponse]:
        """Mengambil seluruh berkas lampiran yang terpasang pada rencana kerja."""
        return _out(await self.service.list_attachments(access))

    async def handle_save_attachments(
        self,
        access: PlanAccess,
        data: AttachmentsRequest,
    ) -> list[AttachmentResponse]:
        """Menyimpan atau memperbarui daftar berkas lampiran pada rencana kerja draf."""
        await ensure_same_org(self.db, access.user.organization_id, files=data.file_ids)
        return _out(await self.service.save_attachments(access, data.file_ids))


__all__ = ["WorkPlanAttachmentsController"]
