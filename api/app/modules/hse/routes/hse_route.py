"""
api/app/modules/hse/routes/hse_route.py

Rute endpoint FastAPI untuk modul HSE (Health, Safety & Environment / HES).
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.api.deps import get_current_user, require_permission
from app.core.list_params import TOTAL_HEADER, ListParams, check_date_range
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.hse.controllers.hse_controller import HseController
from app.modules.hse.dependencies import get_hse_service
from app.modules.hse.schemas.hse_schema import (
    INSPECTION_PERIOD_PATTERN,
    INSPECTION_STATUS_PATTERN,
    HseAcknowledgeCreate,
    HseCampaignAuditStats,
    HseCampaignCreate,
    HseCampaignResponse,
    HseCampaignUpdate,
    InspectionChecklistTemplate,
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
)
async def delete_campaign(
    campaign_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_HSE_CAMPAIGNS)),
    controller: HseController = Depends(get_controller),
) -> dict[str, bool]:
    return await controller.delete_campaign(campaign_id, current_user)


# ================= 2. Gerbang Akseptasi & Audit Pembaca =================

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
)
async def get_campaign_readers(
    campaign_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_HSE_CAMPAIGNS)),
    controller: HseController = Depends(get_controller),
) -> HseCampaignAuditStats:
    return await controller.get_campaign_audit_stats(campaign_id, current_user)


# ================= 3. Inspeksi Keselamatan Kendaraan =================

@router.get(
    "/inspections",
    response_model=list[VehicleInspectionResponse],
    summary="Daftar riwayat inspeksi keselamatan kendaraan",
)
async def list_inspections(
    response: Response,
    params: ListParams = Depends(),
    vehicle_id: UUID | None = Query(None),
    period_type: str | None = Query(None, pattern=INSPECTION_PERIOD_PATTERN),
    status_filter: str | None = Query(None, alias="status", pattern=INSPECTION_STATUS_PATTERN),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100000),
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_VEHICLE_INSPECTIONS)),
    controller: HseController = Depends(get_controller),
) -> list[VehicleInspectionResponse]:
    """`q` = awalan plat/nama kendaraan/nama pemeriksa. `page`/`size` (bila ada) menggantikan `limit`/`offset`;
    total baris di header `X-Total-Count`. Tanpa parameter = perilaku lama (50 terbaru)."""
    check_date_range(from_date, to_date, start_name="from_date", end_name="to_date")
    if params.paged:
        limit, offset = params.size, (params.page - 1) * params.size
    items, total = await controller.list_vehicle_inspections(
        vehicle_id=vehicle_id,
        period_type=period_type,
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
        user=current_user,
        q=params.q,
    )
    response.headers[TOTAL_HEADER] = str(total)
    return items


@router.get(
    "/inspections/mine",
    response_model=list[VehicleInspectionResponse],
    summary="Inspeksi yang saya kirim atau untuk kendaraan yang saya kemudikan",
)
async def my_inspections(
    response: Response,
    params: ListParams = Depends(),
    vehicle_id: UUID | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    controller: HseController = Depends(get_controller),
) -> list[VehicleInspectionResponse]:
    """Milik sendiri: pemeriksa = saya, atau pengemudi aktif kendaraannya. Tanpa page/size: 50 terbaru."""
    check_date_range(from_date, to_date, start_name="from_date", end_name="to_date")
    if not current_user.employee_id:
        response.headers[TOTAL_HEADER] = "0"
        return []
    limit, offset = (params.size, (params.page - 1) * params.size) if params.paged else (50, 0)
    items, total = await controller.list_vehicle_inspections(
        vehicle_id=vehicle_id, from_date=from_date, to_date=to_date, limit=limit, offset=offset,
        user=current_user, q=params.q, mine=str(current_user.employee_id),
    )
    response.headers[TOTAL_HEADER] = str(total)
    return items


@router.get(
    "/inspections/checklist-template",
    response_model=InspectionChecklistTemplate,
    summary="Butir daftar periksa baku untuk layar Buat inspeksi",
)
async def inspection_checklist_template(
    current_user: CurrentUser = Depends(get_current_user),
    controller: HseController = Depends(get_controller),
) -> InspectionChecklistTemplate:
    return controller.inspection_checklist_template()


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
    """HSE (manage:vehicle_inspections, kendaraan di kantornya), pengemudi aktif kendaraan itu, atau ketua tim
    (kendaraan di kantornya). Peran lain 403; kendaraan di luar hak/kantor 404."""
    return await controller.create_vehicle_inspection(data, current_user)


@router.get(
    "/inspections/{inspection_id}",
    response_model=VehicleInspectionResponse,
    summary="Detail inspeksi kendaraan",
)
async def get_inspection(
    inspection_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_VEHICLE_INSPECTIONS)),
    controller: HseController = Depends(get_controller),
) -> VehicleInspectionResponse:
    return await controller.get_vehicle_inspection(inspection_id, current_user)


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

