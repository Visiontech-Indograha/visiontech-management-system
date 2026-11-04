"""
api/app/modules/hse/routes/hse_route.py

Rute endpoint FastAPI untuk modul HSE (Health, Safety & Environment / HES).
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.hse.controllers.hse_controller import HseController
from app.modules.hse.dependencies import get_hse_service
from app.modules.hse.schemas.hse_schema import (
    HseAcknowledgeCreate,
    HseCampaignAuditStats,
    HseCampaignCreate,
    HseCampaignResponse,
    HseCampaignUpdate,
    VehicleInspectionCreate,
    VehicleInspectionResponse,
    VehicleInspectionVerify,
)
from app.modules.hse.services.hse_service import HseService

router = APIRouter(prefix="/hse", tags=["HSE & Keselamatan Kerja"])


def get_controller(service: HseService = Depends(get_hse_service)) -> HseController:
    return HseController(service)


# ================= 1. Kampanye & Materi K3 =================

@router.get(
    "/campaigns",
    response_model=list[HseCampaignResponse],
    summary="Daftar kampanye keselamatan K3",
    dependencies=[Depends(require_permission(Permission.VIEW_HSE_CAMPAIGNS))],
)
async def list_campaigns(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: bool | None = Query(None),
    target_audience: str | None = Query(None),
    controller: HseController = Depends(get_controller),
) -> list[HseCampaignResponse]:
    return await controller.list_campaigns(
        limit=limit,
        offset=offset,
        is_active=is_active,
        target_audience=target_audience,
    )


@router.post(
    "/campaigns",
    response_model=HseCampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat kampanye keselamatan K3 baru",
)
async def create_campaign(
    data: HseCampaignCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_HSE_CAMPAIGNS)),
    controller: HseController = Depends(get_controller),
) -> HseCampaignResponse:
    return await controller.create_campaign(data, current_user)


@router.get(
    "/campaigns/active-popup",
    summary="Ambil popup materi K3 wajib yang belum dibaca pengguna saat ini",
)
async def get_active_popup(
    current_user: CurrentUser = Depends(get_current_user),
    controller: HseController = Depends(get_controller),
) -> dict[str, Any]:
    """
    Dipanggil saat pengguna login atau membuka aplikasi (Web & Mobile).
    Jika mengembalikan kampanye, aplikasi menampilkan Modal Pop-up Non-Skippable
    dengan penghitung waktu mundur (cooldown).
    """
    return await controller.get_active_popup(current_user)


@router.get(
    "/campaigns/{campaign_id}",
    response_model=HseCampaignResponse,
    summary="Detail kampanye K3",
    dependencies=[Depends(require_permission(Permission.VIEW_HSE_CAMPAIGNS))],
)
async def get_campaign(
    campaign_id: UUID,
    controller: HseController = Depends(get_controller),
) -> HseCampaignResponse:
    return await controller.get_campaign(campaign_id)


@router.put(
    "/campaigns/{campaign_id}",
    response_model=HseCampaignResponse,
    summary="Perbarui kampanye K3",
)
async def update_campaign(
    campaign_id: UUID,
    data: HseCampaignUpdate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_HSE_CAMPAIGNS)),
    controller: HseController = Depends(get_controller),
) -> HseCampaignResponse:
    return await controller.update_campaign(campaign_id, data, current_user)


@router.delete(
    "/campaigns/{campaign_id}",
    summary="Hapus kampanye K3 (soft delete)",
    dependencies=[Depends(require_permission(Permission.MANAGE_HSE_CAMPAIGNS))],
)
async def delete_campaign(
    campaign_id: UUID,
    controller: HseController = Depends(get_controller),
) -> dict[str, bool]:
    return await controller.delete_campaign(campaign_id)


# ================= 2. Gerbang Akseptasi & Audit Pembaca =================

@router.post(
    "/campaigns/{campaign_id}/seen",
    summary="Catat popup K3 sudah tampil hari ini (paling banyak sekali sehari per pengguna)",
)
async def mark_campaign_seen(
    campaign_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: HseController = Depends(get_controller),
) -> dict[str, bool]:
    return await controller.mark_popup_seen(campaign_id, current_user)


@router.post(
    "/campaigns/{campaign_id}/acknowledge",
    summary="Konfirmasi telah membaca materi K3 (melewati cooldown & scroll)",
)
async def acknowledge_campaign(
    campaign_id: UUID,
    data: HseAcknowledgeCreate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    controller: HseController = Depends(get_controller),
) -> dict[str, Any]:
    return await controller.acknowledge_campaign(
        campaign_id=campaign_id,
        current_user=current_user,
        data=data,
        request=request,
    )


@router.get(
    "/campaigns/{campaign_id}/readers",
    response_model=HseCampaignAuditStats,
    summary="Audit jejak pengguna yang telah membaca kampanye K3",
    dependencies=[Depends(require_permission(Permission.VIEW_HSE_CAMPAIGNS))],
)
async def get_campaign_readers(
    campaign_id: UUID,
    controller: HseController = Depends(get_controller),
) -> HseCampaignAuditStats:
    return await controller.get_campaign_audit_stats(campaign_id)


# ================= 3. Inspeksi Keselamatan Kendaraan =================

@router.get(
    "/inspections",
    response_model=list[VehicleInspectionResponse],
    summary="Daftar riwayat inspeksi keselamatan kendaraan",
    dependencies=[Depends(require_permission(Permission.VIEW_VEHICLE_INSPECTIONS))],
)
async def list_inspections(
    vehicle_id: UUID | None = Query(None),
    period_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    controller: HseController = Depends(get_controller),
) -> list[VehicleInspectionResponse]:
    return await controller.list_vehicle_inspections(
        vehicle_id=vehicle_id,
        period_type=period_type,
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/inspections",
    response_model=VehicleInspectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kirim formulir inspeksi kendaraan (checklist & foto)",
)
async def create_inspection(
    data: VehicleInspectionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: HseController = Depends(get_controller),
) -> VehicleInspectionResponse:
    return await controller.create_vehicle_inspection(data, current_user)


@router.get(
    "/inspections/{inspection_id}",
    response_model=VehicleInspectionResponse,
    summary="Detail inspeksi kendaraan",
    dependencies=[Depends(require_permission(Permission.VIEW_VEHICLE_INSPECTIONS))],
)
async def get_inspection(
    inspection_id: UUID,
    controller: HseController = Depends(get_controller),
) -> VehicleInspectionResponse:
    return await controller.get_vehicle_inspection(inspection_id)


@router.patch(
    "/inspections/{inspection_id}/verify",
    response_model=VehicleInspectionResponse,
    summary="Verifikasi hasil inspeksi kendaraan oleh HSE / Super Admin",
)
async def verify_inspection(
    inspection_id: UUID,
    data: VehicleInspectionVerify,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_VEHICLE_INSPECTIONS)),
    controller: HseController = Depends(get_controller),
) -> VehicleInspectionResponse:
    return await controller.verify_vehicle_inspection(inspection_id, data, current_user)

