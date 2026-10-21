"""
app/modules/exports/routes/export_route.py

Rute ekspor dokumen resmi (Milestone 8, docs/35 §8). Setiap ekspor tercatat di `document_template_export` dan bisa
diunduh ulang lewat `/exports/{export_id}/file`.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.exports.controllers.export_controller import ExportController
from app.modules.exports.schemas.export_schema import CompletionExportRequest, ExportOut, PeriodicExportRequest

router = APIRouter(prefix="/exports", tags=["Ekspor Dokumen"])
_FILE: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/octet-stream": {}}, "description": "Berkas dokumen"}
}


@router.post("/work-completions/{completion_id}", response_class=Response, responses=_FILE)
async def export_work_completion(
    completion_id: UUID,
    body: CompletionExportRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
) -> Response:
    """BAST (.docx), Survey Report (.docx), BAST resmi ber-QR (.pdf), BoQ (.xlsx), atau slide progres (.pptx)."""
    return await controller.export_completion(current_user, completion_id, body)


@router.get("/work-completions/{completion_id}", response_model=list[ExportOut])
async def list_work_completion_exports(
    completion_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
) -> list[ExportOut]:
    """Riwayat dokumen yang pernah dibuat untuk order ini."""
    return await controller.list_for_completion(current_user, completion_id)


@router.post("/periodic", response_class=Response, responses=_FILE)
async def export_periodic(
    body: PeriodicExportRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: ExportController = Depends(),
) -> Response:
    """Rekap divisi per rentang (maks. 31 hari): jadwal, BoQ & uang makan (.xlsx) atau slide mingguan (.pptx)."""
    return await controller.export_periodic(current_user, body)


@router.get("/periodic", response_model=list[ExportOut])
async def list_periodic_exports(
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: ExportController = Depends(),
) -> list[ExportOut]:
    """Rekap periodik: OM & SUPER_ADMIN melihat semua, PM miliknya sendiri."""
    return await controller.list_periodic(current_user)


@router.get("/{export_id}/file", response_class=Response, responses=_FILE)
async def download_export(
    export_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
) -> Response:
    """Unduh ulang dokumen dari registri (hak sama dengan saat membuatnya)."""
    return await controller.download(current_user, export_id)
