"""
Adendum SK — perpanjangan & personel (V-22, dok 05 §3.4). Tipis: aturan di
services/plan_change_service.py, SQL di crud/crud_plan_change.py.

Sebelumnya: `/plans/{id}/changes/extension` + `/{change_id}/approve` yang langsung MENERAPKAN
perubahan saat PM menyetujui — tanpa penerimaan ketua, tanpa dokumen adendum, dan PERSONNEL tidak
pernah bisa diajukan lewat API.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_plan_change_service
from app.core.security import CurrentUser
from app.schemas.plan_change import ChangeRequest, ChangeResponse, DecisionRequest
from app.services.plan_change_service import PlanChangeService

plan_router = APIRouter(prefix="/work-plans/{plan_id}/changes", tags=["Plan Changes / Addendums"])
router = APIRouter(prefix="/changes", tags=["Plan Changes / Addendums"])








async def _read(service: PlanChangeService, change_id: Any) -> ChangeResponse:
    return ChangeResponse(**(await service.read(change_id))._mapping)


@plan_router.post("", response_model=ChangeResponse, status_code=status.HTTP_201_CREATED)
async def request_change(
    plan_id: UUID,
    data: ChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    plan_change_service: PlanChangeService = Depends(get_plan_change_service),
) -> ChangeResponse:
    """
    Mengajukan adendum perubahan pada SK (POST).
    REQUEST_CHANGE (ketua, perpanjangan) · REQUEST_PERSONNEL_CHANGE (PM unit/OPS, personel).
    
    Path Parameters:
    - plan_id (UUID): ID dari SK.
    
    Request Body:
    - data (ChangeRequest): Data usulan perubahan (jenis perubahan, periode baru, dsb).
    
    Returns:
    - ChangeResponse: Data respons dari perubahan yang diusulkan.
    """
    # Menggunakan Dependency Injection untuk mendapatkan user (get_current_user) dan service adendum
    # Logika Service layer dipanggil berdasarkan tipe perubahan (EXTEND atau lainnya)
    service = plan_change_service
    if data.type == "EXTEND":
        change_id = await service.request_change(plan_id, current_user, data.new_period_end, data.reason)
    else:
        change_id = await service.request_personnel_change(
            plan_id, current_user, data.leader_employee_id, data.member_employee_ids, data.reason)
    return await _read(plan_change_service, change_id)


@router.post("/{change_id}/approve", response_model=ChangeResponse)
async def approve_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    plan_change_service: PlanChangeService = Depends(get_plan_change_service),
) -> ChangeResponse:
    """
    Menyetujui adendum perpanjangan SK (POST).
    APPROVE_CHANGE — PM unit/OPS menandatangani perpanjangan.
    
    Path Parameters:
    - change_id (UUID): ID perubahan adendum.
    
    Request Body:
    - data (DecisionRequest): Persetujuan atau keputusan.
    
    Returns:
    - ChangeResponse: Status terbaru adendum setelah disetujui.
    """
    # Memanggil Dependency (get_current_user) dan PlanChangeService
    # Meneruskan eksekusi persetujuan ke Service layer
    return await _read(plan_change_service, await plan_change_service.approve_change(change_id, current_user))


@router.post("/{change_id}/accept", response_model=ChangeResponse)
async def accept_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    plan_change_service: PlanChangeService = Depends(get_plan_change_service),
) -> ChangeResponse:
    """
    Menerima dan mengaktifkan adendum (POST).
    ACCEPT_CHANGE — ketua (perpanjangan) / ketua baru (personel) mengaktifkan adendum.
    
    Path Parameters:
    - change_id (UUID): ID usulan adendum.
    
    Request Body:
    - data (DecisionRequest): Konfirmasi penerimaan.
    
    Returns:
    - ChangeResponse: Status adendum terbaru.
    """
    # Memeriksa user saat ini menggunakan Dependency Injection
    # Mengirim perintah pengaktifan adendum ke layer Service
    return await _read(plan_change_service, await plan_change_service.accept_change(change_id, current_user))


@router.post("/{change_id}/reject", response_model=ChangeResponse)
async def reject_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    plan_change_service: PlanChangeService = Depends(get_plan_change_service),
) -> ChangeResponse:
    """
    Menolak adendum (POST).
    REJECT_CHANGE — alasan wajib disertakan.
    
    Path Parameters:
    - change_id (UUID): ID adendum.
    
    Request Body:
    - data (DecisionRequest): Alasan penolakan.
    
    Returns:
    - ChangeResponse: Status adendum yang ditolak.
    """
    # Inject dependensi user saat ini dan PlanChangeService
    # Meneruskan alasan penolakan ke Service layer
    return await _read(plan_change_service, await plan_change_service.reject_change(change_id, current_user, data.reason))


@router.post("/{change_id}/withdraw", response_model=ChangeResponse)
async def withdraw_change(
    change_id: UUID,
    data: DecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    plan_change_service: PlanChangeService = Depends(get_plan_change_service),
) -> ChangeResponse:
    """
    Menarik kembali usulan adendum personel (POST).
    WITHDRAW_CHANGE — PM menarik adendum personel.
    
    Path Parameters:
    - change_id (UUID): ID usulan adendum.
    
    Request Body:
    - data (DecisionRequest): Alasan pembatalan.
    
    Returns:
    - ChangeResponse: Status adendum yang ditarik.
    """
    # Dependency Injection untuk mengidentifikasi pengguna (get_current_user)
    # Memanggil PlanChangeService untuk melakukan pencabutan (withdraw)
    return await _read(plan_change_service, await plan_change_service.withdraw_change(change_id, current_user, data.reason))
