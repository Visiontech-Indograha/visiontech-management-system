"""
app/modules/work_completion/routes/work_completion_route.py

Definisi rute endpoint FastAPI untuk modul Order Proyek Klien (Work Completion) VMS V3.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.work_completion.controllers.work_completion_controller import WorkCompletionController
from app.modules.work_completion.schemas.work_completion_schema import (
    SyncBomFromWorkTypesIn,
    WorkCompletionAccDecision,
    WorkCompletionBomIn,
    WorkCompletionBomOut,
    WorkCompletionBomUpdate,
    WorkCompletionCreate,
    WorkCompletionListOut,
    WorkCompletionOut,
    WorkCompletionRevisionCreate,
    WorkCompletionRevisionOut,
    WorkCompletionSignRequest,
    WorkCompletionStatusUpdate,
    WorkCompletionUpdate,
    WorkCompletionVerifyOut,
)

_PLANNER = Depends(require_permission(Permission.CREATE_PLAN))
router = APIRouter(prefix="/work-completions", tags=["Work Completions (Order Klien)"])


@router.get("", response_model=WorkCompletionListOut, summary="Daftar Order Proyek Klien")
async def list_work_completions(
    division_id: UUID | None = Query(None, description="Filter divisi"),
    order_status: str | None = Query(None, description="Filter status (PENDING, ONGOING, URGENT, COMPLETED)"),
    search: str | None = Query(None, description="Pencarian nama klien, judul proyek, atau nomor SPK"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionListOut:
    return await controller.list_orders(
        current_user=current_user,
        division_id=division_id,
        status=order_status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=WorkCompletionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Buat Order Proyek Klien Baru",
)
async def create_work_completion(
    body: WorkCompletionCreate,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionOut:
    return await controller.create_order(body, current_user)


@router.get("/{completion_id}", response_model=WorkCompletionOut, summary="Detail Order Proyek Klien")
async def get_work_completion(
    completion_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionOut:
    return await controller.get_order(completion_id, current_user)


@router.delete("/{completion_id}/photos/{file_id}", response_model=WorkCompletionOut,
               summary="Hapus Foto Realisasi BAST")
async def delete_work_completion_photo(
    completion_id: UUID,
    file_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionOut:
    """Ketua tim/PM menghapus satu foto realisasi selama BAST belum disahkan PM (langsung tersimpan)."""
    return await controller.remove_photo(completion_id, file_id, current_user)


@router.get("/{completion_id}/signatures/{role}", response_class=Response, summary="Gambar Tanda Tangan BAST",
            responses={200: {"content": {"image/png": {}}}})
async def get_work_completion_signature(
    completion_id: UUID,
    role: Literal["leader", "pm"],
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkCompletionController = Depends(),
) -> Response:
    """Tanda tangan ketua/PM yang sudah tersimpan (ditampilkan kembali di layar BAST)."""
    return await controller.signature(completion_id, role, current_user)


@router.put("/{completion_id}", response_model=WorkCompletionOut, summary="Perbarui Data Order Proyek Klien")
async def update_work_completion(
    completion_id: UUID,
    body: WorkCompletionUpdate,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionOut:
    return await controller.update_order(completion_id, body, current_user)


@router.patch(
    "/{completion_id}/status",
    response_model=WorkCompletionOut,
    summary="Perbarui Status Order (PM Override)",
)
async def update_work_completion_status(
    completion_id: UUID,
    body: WorkCompletionStatusUpdate,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionOut:
    return await controller.update_status(completion_id, body, current_user)


@router.delete(
    "/{completion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus Order Proyek Klien (Soft Delete)",
)
async def delete_work_completion(
    completion_id: UUID,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> None:
    await controller.delete_order(completion_id, current_user)


@router.post(
    "/{completion_id}/sign",
    response_model=WorkCompletionOut,
    summary="Tanda Tangan Digital Berita Acara Penyelesaian",
)
async def sign_work_completion(
    completion_id: UUID,
    body: WorkCompletionSignRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionOut:
    return await controller.sign_order(completion_id, body, current_user)


@router.get(
    "/{completion_id}/bom",
    response_model=list[WorkCompletionBomOut],
    summary="Daftar Item BoM Order Proyek Klien",
)
async def list_work_completion_bom(
    completion_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkCompletionController = Depends(),
) -> list[WorkCompletionBomOut]:
    return await controller.list_bom_items(completion_id, current_user)


@router.post(
    "/{completion_id}/bom",
    response_model=WorkCompletionBomOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah Item BoM ke Order Proyek Klien",
)
async def add_work_completion_bom(
    completion_id: UUID,
    body: WorkCompletionBomIn,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionBomOut:
    return await controller.add_bom_item(completion_id, body, current_user)


@router.put(
    "/bom/{bom_id}",
    response_model=WorkCompletionBomOut,
    summary="Perbarui Item BoM (Realisasi Aktual Lapangan)",
)
async def update_work_completion_bom(
    bom_id: UUID,
    body: WorkCompletionBomUpdate,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionBomOut:
    return await controller.update_bom_item(bom_id, body, current_user)


@router.delete(
    "/bom/{bom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus Item BoM",
)
async def delete_work_completion_bom(
    bom_id: UUID,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> Response:
    await controller.delete_bom_item(bom_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{completion_id}/sync-bom",
    summary="Sinkronisasi Otomatis BoM dari Template Jenis Pekerjaan",
)
async def sync_bom_from_work_types(
    completion_id: UUID,
    body: SyncBomFromWorkTypesIn | None = None,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> dict[str, Any]:
    overwrite = body.overwrite_existing if body else False
    return await controller.sync_bom(completion_id, overwrite, current_user)


@router.post(
    "/{completion_id}/acc-decision",
    response_model=WorkCompletionOut,
    summary="Keputusan ACC Klien (MENUNGGU_ACC, DITERIMA, DITOLAK_REWORK)",
)
async def decide_acc_status(
    completion_id: UUID,
    body: WorkCompletionAccDecision,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionOut:
    return await controller.decide_acc(completion_id, body, current_user)


@router.post(
    "/{completion_id}/revisions",
    status_code=status.HTTP_201_CREATED,
    summary="Catat Revisi / Tambahan Pekerjaan dari Klien",
)
async def create_revision(
    completion_id: UUID,
    body: WorkCompletionRevisionCreate,
    current_user: CurrentUser = _PLANNER,
    controller: WorkCompletionController = Depends(),
) -> dict[str, Any]:
    return await controller.create_revision(completion_id, body, current_user)


@router.get(
    "/{completion_id}/revisions",
    response_model=list[WorkCompletionRevisionOut],
    summary="Daftar Revisi Klien",
)
async def list_revisions(
    completion_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkCompletionController = Depends(),
) -> list[WorkCompletionRevisionOut]:
    return await controller.list_revisions(completion_id, current_user)


# Halaman verifikasi QR dibuka siapa saja yang memegang dokumen: tanpa login, wajib sidik SHA-256 lengkap.
verify_router = APIRouter(prefix="/verify", tags=["Verifikasi Dokumen"])


@verify_router.get("/work-completions/{completion_id}", response_model=WorkCompletionVerifyOut)
async def verify_work_completion(
    completion_id: UUID,
    h: str = Query(..., min_length=64, max_length=64, pattern="^[0-9a-fA-F]{64}$"),
    controller: WorkCompletionController = Depends(),
) -> WorkCompletionVerifyOut:
    """Cek keaslian BAST resmi: sidik cocok dan isi tidak berubah sejak disahkan PM. Sidik salah → 404."""
    return await controller.verify(completion_id, h)
