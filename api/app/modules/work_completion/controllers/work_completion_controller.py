"""
app/modules/work_completion/controllers/work_completion_controller.py

Controller HTTP untuk orkestrasi endpoint Order Proyek Klien (Work Completion) VMS V3.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB_SCOPE, get_db
from app.core.security import CurrentUser
from app.modules.work_completion.crud.crud_work_completion import CRUDWorkCompletion
from app.modules.work_completion.schemas.work_completion_schema import (
    WorkCompletionBomIn,
    WorkCompletionBomOut,
    WorkCompletionBomUpdate,
    WorkCompletionCreate,
    WorkCompletionListOut,
    WorkCompletionOut,
    WorkCompletionSignRequest,
    WorkCompletionStatusUpdate,
    WorkCompletionUpdate,
)
from app.modules.work_completion.services.work_completion_service import WorkCompletionService


def get_work_completion_service(db: AsyncSession = Depends(get_db, scope=DB_SCOPE)) -> WorkCompletionService:
    """Dependency injector untuk WorkCompletionService."""
    crud = CRUDWorkCompletion(db)
    return WorkCompletionService(crud)


class WorkCompletionController:
    """Controller penanganan request HTTP Work Completion."""

    def __init__(self, service: WorkCompletionService = Depends(get_work_completion_service)) -> None:
        self.service = service

    async def list_orders(
        self,
        current_user: CurrentUser,
        division_id: UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> WorkCompletionListOut:
        """Daftar order proyek klien."""
        items, total = await self.service.list_orders(
            current_user,
            division_id=division_id,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )
        return WorkCompletionListOut(
            items=[WorkCompletionOut(**it) for it in items],
            total=total,
        )

    async def get_order(
        self,
        completion_id: UUID,
        current_user: CurrentUser,
    ) -> WorkCompletionOut:
        """Detail order proyek klien."""
        data = await self.service.get_order_detail(current_user, completion_id)
        return WorkCompletionOut(**data)

    async def create_order(
        self,
        body: WorkCompletionCreate,
        current_user: CurrentUser,
    ) -> WorkCompletionOut:
        """Buat order proyek baru."""
        data = await self.service.create_order(current_user, body.model_dump())
        return WorkCompletionOut(**data)

    async def update_order(
        self,
        completion_id: UUID,
        body: WorkCompletionUpdate,
        current_user: CurrentUser,
    ) -> WorkCompletionOut:
        """Update data order proyek."""
        data = await self.service.update_order(current_user, completion_id, body.model_dump(exclude_unset=True))
        return WorkCompletionOut(**data)

    async def update_status(
        self,
        completion_id: UUID,
        body: WorkCompletionStatusUpdate,
        current_user: CurrentUser,
    ) -> WorkCompletionOut:
        """Ubah status order proyek (PM Override)."""
        data = await self.service.update_order_status(
            current_user,
            completion_id,
            body.order_status,
            body.notes,
        )
        return WorkCompletionOut(**data)

    async def sign_order(
        self,
        completion_id: UUID,
        body: WorkCompletionSignRequest,
        current_user: CurrentUser,
    ) -> WorkCompletionOut:
        """Tanda tangan digital berita acara penyelesaian order."""
        data = await self.service.sign_order(
            current_user,
            completion_id,
            signature_data_url=body.signature_data_url,
            summary_notes=body.summary_notes,
            obstacles=body.obstacles,
            realization_photos=body.realization_photos,
        )
        return WorkCompletionOut(**data)

    async def list_bom_items(
        self,
        completion_id: UUID,
        current_user: CurrentUser,
    ) -> list[WorkCompletionBomOut]:
        """Daftar item BoM suatu order klien."""
        rows = await self.service.list_bom_items(current_user, completion_id)
        return [WorkCompletionBomOut(**r) for r in rows]

    async def add_bom_item(
        self,
        completion_id: UUID,
        body: WorkCompletionBomIn,
        current_user: CurrentUser,
    ) -> WorkCompletionBomOut:
        """Menambahkan item BoM baru ke order klien."""
        row = await self.service.add_bom_item(current_user, completion_id, body.model_dump())
        return WorkCompletionBomOut(**row)

    async def update_bom_item(
        self,
        bom_id: UUID,
        body: WorkCompletionBomUpdate,
        current_user: CurrentUser,
    ) -> WorkCompletionBomOut:
        """Memperbarui item BoM (misal: pengisian realisasi pemakaian aktual di lapangan)."""
        row = await self.service.update_bom_item(current_user, bom_id, body.model_dump(exclude_unset=True))
        return WorkCompletionBomOut(**row)

    async def delete_bom_item(
        self,
        bom_id: UUID,
        current_user: CurrentUser,
    ) -> None:
        """Menghapus item BoM."""
        await self.service.delete_bom_item(current_user, bom_id)

    async def sync_bom(
        self,
        completion_id: UUID,
        overwrite_existing: bool,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        """Sinkronisasi otomatis template BoM dari jenis pekerjaan."""
        synced_count = await self.service.sync_bom_from_work_types(
            current_user, completion_id, overwrite_existing=overwrite_existing
        )
        return {
            "success": True,
            "completion_id": completion_id,
            "synced_materials_count": synced_count,
            "message": f"Berhasil menyinkronkan {synced_count} material dari template jenis pekerjaan.",
        }

    async def export_docx(
        self,
        completion_id: UUID,
        current_user: CurrentUser,
    ) -> tuple[bytes, str]:
        """Ekspor dokumen Berita Acara & BoM dalam format Word (.docx)."""
        return await self.service.export_completion_docx(current_user, completion_id)
