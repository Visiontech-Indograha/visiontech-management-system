"""
app/modules/work_orders/routes/work_order_route.py

Rute REST API untuk modul Work Orders VMS V2.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.list_params import ListParams, apply_list
from app.core.security import CurrentUser
from app.modules.work_orders.controllers.work_order_controller import WorkOrderController
from app.modules.work_orders.schemas.work_order_schema import (
    SurveySubmitIn,
    TeamSurveyOut,
    WorkOrderAssignSurvey,
    WorkOrderCreate,
    WorkOrderDetailOut,
    WorkOrderOut,
    WorkOrderSignBast,
)

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


class ItemProgressIn(BaseModel):
    completed_qty: Decimal = Field(default=Decimal("1.0"), ge=0)
    status: str = Field(default="DONE")
    photo_slots_snapshot: list[dict[str, Any]] | None = None


class BomActualIn(BaseModel):
    actual_qty: Decimal = Field(..., ge=0)


@router.get("", response_model=list[WorkOrderOut])
async def list_work_orders(
    division_id: UUID | None = None,
    status: str | None = None,
    client_id: UUID | None = None,
    pm_id: UUID | None = None,
    lead_team_id: UUID | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> list[WorkOrderOut]:
    """Daftar work orders dengan filter status, divisi, klien, dan pencarian."""
    return await controller.list_work_orders(
        current_user=current_user,
        division_id=division_id,
        status=status,
        client_id=client_id,
        pm_id=pm_id,
        lead_team_id=lead_team_id,
        q=q,
        limit=limit,
    )


@router.post("", response_model=WorkOrderDetailOut, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    data: WorkOrderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> WorkOrderDetailOut:
    """Buat Work Order baru dari klien (Status awal: WAITING_SURVEY)."""
    return await controller.create_work_order(current_user, data)


@router.get("/team-surveys", response_model=list[TeamSurveyOut])
async def list_team_surveys(
    response: Response,
    params: ListParams = Depends(),
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> list[TeamSurveyOut]:
    """Survei WO aktif milik tim yang diikuti pemanggil (ketua atau anggota aktif), untuk layar survei di HP.
    Hanya WO berstatus SURVEY_IN_PROGRESS dan survei belum dikirim/disetujui. Cakupan = keanggotaan tim."""
    rows = await controller.list_team_surveys(current_user)
    return list(
        apply_list(
            rows, params, response,
            lambda r: (r.wo_number, r.title, r.client_name, r.site_name, r.surveyor_team_name),
            prefix=True,
        )
    )


@router.get("/{work_order_id}", response_model=WorkOrderDetailOut)
async def get_work_order(
    work_order_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> WorkOrderDetailOut:
    """Detail lengkap Work Order termasuk titik survei, item pekerjaan, dan BoM."""
    return await controller.get_work_order(current_user, work_order_id)


@router.post("/{work_order_id}/assign-survey", response_model=WorkOrderDetailOut)
async def assign_survey(
    work_order_id: UUID,
    data: WorkOrderAssignSurvey,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> WorkOrderDetailOut:
    """PM menugaskan tim dan jadwal untuk survei lapangan."""
    return await controller.assign_survey(current_user, work_order_id, data)


@router.post("/{work_order_id}/submit-survey", response_model=WorkOrderDetailOut)
async def submit_survey(
    work_order_id: UUID,
    data: SurveySubmitIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> WorkOrderDetailOut:
    """Ketua Tim mengirimkan laporan survei lapangan dari aplikasi mobile / web."""
    return await controller.submit_survey(current_user, work_order_id, data)


@router.post("/{work_order_id}/apply-survey", response_model=WorkOrderDetailOut)
async def apply_survey(
    work_order_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> WorkOrderDetailOut:
    """
    Fitur Inti: PM menyetujui survei dan mengunci item tugas & BOM (Status: READY_TO_EXECUTE).
    """
    return await controller.apply_survey(current_user, work_order_id)


@router.post("/{work_order_id}/sign-bast", response_model=WorkOrderDetailOut)
async def sign_bast(
    work_order_id: UUID,
    data: WorkOrderSignBast,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> WorkOrderDetailOut:
    """Penandatanganan Berita Acara Serah Terima (BAST) pekerjaan klien."""
    return await controller.sign_bast(current_user, work_order_id, data)


@router.put("/items/{item_id}/progress")
async def update_item_progress(
    item_id: UUID,
    data: ItemProgressIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> dict[str, str]:
    """Perbarui progres dan pemenuhan syarat foto item pekerjaan lapangan."""
    return await controller.update_item_progress(
        current_user,
        item_id,
        data.completed_qty,
        data.status,
        data.photo_slots_snapshot,
    )


@router.put("/bom/{bom_id}/actual")
async def update_bom_actual(
    bom_id: UUID,
    data: BomActualIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> dict[str, str]:
    """Catat penggunaan aktual material (actual BOM) pekerjaan."""
    return await controller.update_bom_actual(current_user, bom_id, data.actual_qty)


@router.get("/{work_order_id}/export/{template}")
async def export_work_order_document(
    work_order_id: UUID,
    template: str,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkOrderController = Depends(),
) -> Response:
    """Unduh dokumen resmi Work Order: BAST (PDF/Word), Laporan Survei, Surat Tugas, BoQ, atau Slide PPTX."""
    filename, media_type, content = await controller.export_document(
        current_user, work_order_id, template
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
