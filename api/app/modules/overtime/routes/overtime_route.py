"""
app/modules/overtime/routes/overtime_route.py

Rute endpoint HTTP untuk pengajuan lembur (/overtime).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import IdempotencyGuard, get_current_user, idempotency_guard, require_permission
from app.core.keyset import cursor_query, finish_page, parse_cursor
from app.core.list_params import ListParams, apply_list
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.overtime.controllers.overtime_controller import OvertimeController
from app.modules.overtime.dependencies import get_overtime_attachments
from app.modules.overtime.schemas.overtime_schema import (
    OvertimeCreate,
    OvertimeResponse,
    OvertimeReview,
)
from app.shared.attachments.schema import AttachmentAdd, AttachmentOut
from app.shared.attachments.service import AttachmentService

router = APIRouter(prefix="/overtime", tags=["Overtime"])


@router.post("", response_model=OvertimeResponse, status_code=status.HTTP_201_CREATED)
async def report_overtime(
    data: OvertimeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
    idem: IdempotencyGuard = Depends(idempotency_guard),
) -> OvertimeResponse | Response:
    """Mengajukan lembur atas jadwal harian yang sedang berjalan (ketua/anggota tim). Mendukung Idempotency-Key."""
    tersimpan = idem.tersimpan()
    if tersimpan is not None:
        return tersimpan
    hasil = await controller.handle_report(current_user, data)
    return await idem.simpan(hasil, status.HTTP_201_CREATED)


@router.get("", response_model=list[OvertimeResponse])
async def list_overtime(
    response: Response,
    params: ListParams = Depends(),
    cursor: str | None = cursor_query(),
    status: str | None = Query(None, max_length=30, description="Filter status lembur"),
    daily_plan_id: UUID | None = Query(None, description="ID jadwal harian"),
    work_plan_id: UUID | None = Query(None, description="Alias daily_plan_id"),
    mine: bool = Query(False, description="true = hanya lembur milik pemanggil (hanya mempersempit cakupan)"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
) -> list[OvertimeResponse]:
    """Daftar lembur untuk satu jadwal harian.

    Mode keyset: `cursor` ada (boleh kosong) -> `size` (bawaan 20), header `X-Next-Cursor`, tanpa `X-Total-Count`;
    `q` = awalan nama karyawan, `status` disaring di SQL.
    """
    after = parse_cursor(cursor, ("datetime", "uuid"))
    if after is not None:
        found = await controller.handle_list(
            current_user, daily_plan_id or work_plan_id, after=after, limit=params.size + 1, status=status, q=params.q,
            mine=mine,
        )
        return finish_page(found, params.size, response, lambda r: (r.created_at, r.id))
    rows = await controller.handle_list(current_user, daily_plan_id or work_plan_id, mine=mine)
    return list(
        apply_list(
            rows,
            params,
            response,
            lambda r: (r.employee_name, r.reason),
            extra=lambda r: status is None or r.status == status,
        )
    )


@router.post("/{ot_id}/review", response_model=OvertimeResponse)
async def review_overtime(
    ot_id: UUID,
    data: OvertimeReview,
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
) -> OvertimeResponse:
    """Menyetujui atau menolak pengajuan lembur."""
    return await controller.handle_review(current_user, ot_id, data)


@router.delete("/{ot_id}")
async def delete_overtime(
    ot_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.DELETE_ANY)),
    controller: OvertimeController = Depends(),
) -> dict[str, str]:
    """Hapus permanen pengajuan lembur — hanya SUPER_ADMIN."""
    return await controller.handle_delete(current_user, ot_id)


@router.get("/{ot_id}/attachments", response_model=list[AttachmentOut])
async def list_overtime_attachments(
    ot_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: AttachmentService = Depends(get_overtime_attachments),
) -> list[dict[str, Any]]:
    """Lampiran lembur (maksimal 5): pemohon dan peninjaunya. Orang lain di kantor yang sama 403; kantor lain 404."""
    return await service.items(current_user, ot_id)


@router.post("/{ot_id}/attachments", response_model=list[AttachmentOut], status_code=status.HTTP_201_CREATED)
async def add_overtime_attachment(
    ot_id: UUID,
    data: AttachmentAdd,
    current_user: CurrentUser = Depends(get_current_user),
    service: AttachmentService = Depends(get_overtime_attachments),
) -> list[dict[str, Any]]:
    """Melampirkan berkas unggahan sendiri (POST /files/upload). Hanya selagi pengajuan menunggu keputusan (409
    LAMPIRAN_TERKUNCI sesudahnya); batas 5 berkas (409 LAMPIRAN_PENUH). Mengulang berkas yang sama aman."""
    return await service.add(current_user, ot_id, data.file_id)


@router.delete("/{ot_id}/attachments/{file_id}", response_model=list[AttachmentOut])
async def remove_overtime_attachment(
    ot_id: UUID,
    file_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: AttachmentService = Depends(get_overtime_attachments),
) -> list[dict[str, Any]]:
    """Menghapus lampiran (pemohon: semua; peninjau: miliknya) selagi pengajuan menunggu keputusan."""
    return await service.remove(current_user, ot_id, file_id)
