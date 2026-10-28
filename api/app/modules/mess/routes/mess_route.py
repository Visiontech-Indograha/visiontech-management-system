"""
app/modules/mess/routes/mess_route.py
Rute API HTTP mess karyawan: master mess (company_mess) dan hunian (company_mess_stay).
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_current_user, require_permission
from app.core.list_params import ListParams, apply_list, check_date_range
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.mess.controllers.mess_controller import MessController
from app.modules.mess.schemas.mess_schema import (
    MessDecision,
    MessPlaceIn,
    MessPlaceOut,
    MessPlaceUpdate,
    MessStayCreate,
    MessStayOut,
    MessStayRequest,
    MessStayUpdate,
)

router = APIRouter(prefix="/mess", tags=["Mess"])
_VIEW = Depends(require_permission(Permission.VIEW_MESS))
_MANAGE = Depends(require_permission(Permission.MANAGE_MESS))
_REVIEW = Depends(require_permission(Permission.REVIEW_MESS))


@router.get("/places", response_model=list[MessPlaceOut])
async def list_places(
    response: Response,
    params: ListParams = Depends(),
    current_user: CurrentUser = Depends(get_current_user),
    controller: MessController = Depends(),
) -> list[MessPlaceOut]:
    """Daftar mess yang bisa dipilih (nama, alamat, kapasitas, jumlah penghuni hari ini); semua akun login."""
    rows = await controller.handle_list_places(current_user)
    return list(apply_list(rows, params, response, lambda p: (p.mess_name, p.city, p.address)))


@router.post("/places", response_model=MessPlaceOut, status_code=201)
async def create_place(
    data: MessPlaceIn,
    current_user: CurrentUser = _MANAGE,
    controller: MessController = Depends(),
) -> MessPlaceOut:
    """Menambah mess ke daftar master."""
    return await controller.handle_create_place(current_user, data)


@router.put("/places/{mess_id}", response_model=MessPlaceOut)
async def update_place(
    mess_id: UUID,
    data: MessPlaceUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: MessController = Depends(),
) -> MessPlaceOut:
    """Memperbarui data mess di master."""
    return await controller.handle_update_place(current_user, mess_id, data)


@router.delete("/places/{mess_id}")
async def delete_place(
    mess_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: MessController = Depends(),
) -> dict[str, str]:
    """Menghapus mess dari daftar (ditolak bila masih dihuni / ada pengajuan aktif)."""
    return await controller.handle_delete_place(current_user, mess_id)


@router.get("", response_model=list[MessStayOut])
async def list_stays(
    response: Response,
    params: ListParams = Depends(),
    employee_id: UUID | None = Query(None, description="Filter berdasarkan ID karyawan"),
    start: date | None = Query(None, description="Hunian yang beririsan sejak tanggal ini"),
    end: date | None = Query(None, description="Hunian yang beririsan sampai tanggal ini"),
    status: str | None = Query(None, pattern="^(REQUESTED|APPROVED|REJECTED|CANCELLED)$"),
    current_user: CurrentUser = _VIEW,
    controller: MessController = Depends(),
) -> list[MessStayOut]:
    """Mengambil daftar riwayat, jadwal hunian, dan pengajuan mess karyawan."""
    check_date_range(start, end, start_name="start", end_name="end")
    rows = await controller.handle_list_stays(current_user, employee_id, start, end, status)
    hay = lambda r: (r.employee_name, r.employee_no, r.mess_name, r.city, r.request_note)  # noqa: E731
    return list(apply_list(rows, params, response, hay))


@router.get("/me", response_model=list[MessStayOut])
async def my_stays(
    response: Response,
    params: ListParams = Depends(),
    current_user: CurrentUser = Depends(get_current_user),
    controller: MessController = Depends(),
) -> list[MessStayOut]:
    """Riwayat, jadwal, dan pengajuan hunian mess milik sendiri (tanpa izin view:mess; hanya data akun ini)."""
    rows = await controller.handle_my_stays(current_user)
    return list(apply_list(rows, params, response, lambda r: (r.mess_name, r.city, r.address, r.request_note)))


@router.post("/requests", response_model=MessStayOut, status_code=201)
async def request_stay(
    data: MessStayRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: MessController = Depends(),
) -> MessStayOut:
    """Karyawan mengajukan hunian di mess pilihannya (employee_id dari token); diputus PM/OM/HR."""
    return await controller.handle_request_stay(current_user, data)


@router.get("/{mess_stay_id}", response_model=MessStayOut)
async def get_stay(
    mess_stay_id: UUID,
    current_user: CurrentUser = _VIEW,
    controller: MessController = Depends(),
) -> MessStayOut:
    """Mengambil detail hunian mess karyawan."""
    return await controller.handle_get_stay(current_user, mess_stay_id)


@router.post("", response_model=MessStayOut, status_code=201)
async def create_stay(
    data: MessStayCreate,
    current_user: CurrentUser = _MANAGE,
    controller: MessController = Depends(),
) -> MessStayOut:
    """HR/GA mencatat hunian: karyawan + mess dari master, langsung disetujui."""
    return await controller.handle_create_stay(current_user, data)


@router.post("/{mess_stay_id}/decision", response_model=MessStayOut)
async def decide_stay(
    mess_stay_id: UUID,
    data: MessDecision,
    current_user: CurrentUser = _REVIEW,
    controller: MessController = Depends(),
) -> MessStayOut:
    """PM divisi / OM / HR menyetujui atau menolak pengajuan hunian (penolakan wajib beralasan)."""
    return await controller.handle_decide(current_user, mess_stay_id, data)


@router.post("/{mess_stay_id}/cancel", response_model=MessStayOut)
async def cancel_stay(
    mess_stay_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: MessController = Depends(),
) -> MessStayOut:
    """Pemohon (atau HR/GA) membatalkan pengajuan / hunian yang belum dimulai."""
    return await controller.handle_cancel(current_user, mess_stay_id)


@router.post("/{mess_stay_id}/end", response_model=MessStayOut)
async def end_stay(
    mess_stay_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: MessController = Depends(),
) -> MessStayOut:
    """Penghuni (atau HR/GA) menyelesaikan hunian yang sedang berjalan; riwayat tetap tersimpan."""
    return await controller.handle_end(current_user, mess_stay_id)


@router.put("/{mess_stay_id}", response_model=MessStayOut)
async def update_stay(
    mess_stay_id: UUID,
    data: MessStayUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: MessController = Depends(),
) -> MessStayOut:
    """Mengubah periode hunian."""
    return await controller.handle_update_stay(current_user, mess_stay_id, data)


@router.delete("/{mess_stay_id}")
async def delete_stay(
    mess_stay_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: MessController = Depends(),
) -> dict[str, str]:
    """Menghapus data hunian mess karyawan."""
    return await controller.handle_delete_stay(current_user, mess_stay_id)
