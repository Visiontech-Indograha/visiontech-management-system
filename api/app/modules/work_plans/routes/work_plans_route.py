"""
app/modules/work_plans/routes/work_plans_route.py

Rute endpoint HTTP untuk manajemen rencana kerja / SK (/work-plans).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse, Response

from app.api.deps import (
    get_current_user,
    plan_access,
    plan_day_access,
    require_permission,
)
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.work_plans.controllers.work_plan_controller import (
    WorkPlanController,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    DayPlanRequest,
    PlanAssignmentOptions,
    PlanDayCreate,
    PlanDayResponse,
    PlanDetailOut,
    PlanDraftRequest,
    PlanFormOptions,
    PlanTaskCreate,
    PlanTaskResponse,
    RescheduleItemRequest,
    RescheduleItemResponse,
    WorkPlanCreate,
    WorkPlanResponse,
    WorkPlanUpdate,
)
from app.services.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans", tags=["Work Plans"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))
_DAY_PM_UNIT_ACCESS = Depends(plan_day_access(PlanNeed.PM_UNIT))


@router.get("/assignment-options", response_model=PlanAssignmentOptions)
async def assignment_options(
    period_start: date = Query(...),
    period_end: date = Query(...),
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: WorkPlanController = Depends(),
) -> PlanAssignmentOptions:
    """Mengambil pilihan PM/personel yang sah untuk periode SK baru (R-23) (GET)."""
    return await controller.handle_assignment_options(current_user, period_start, period_end)


@router.get("/form-options", response_model=PlanFormOptions)
async def form_options(
    plan_id: UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: WorkPlanController = Depends(),
) -> PlanFormOptions:
    """Mengambil pilihan untuk form "Buat SK" pada alur v2 (SK2-A/B) (GET)."""
    return await controller.handle_form_options(current_user, plan_id)


@router.get("/driver-options", response_model=list[UUID])
async def driver_options(
    vehicle_id: UUID,
    period_end: date,
    candidate_ids: list[UUID] = Query(default=[]),
    plan_id: UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: WorkPlanController = Depends(),
) -> list[str]:
    """Mengambil daftar calon pengemudi (driver) yang valid (GET)."""
    return await controller.handle_driver_options(current_user, vehicle_id, period_end, candidate_ids, plan_id)


@router.post("/full", response_model=PlanDetailOut, status_code=status.HTTP_201_CREATED)
async def create_full_plan(
    data: PlanDraftRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: WorkPlanController = Depends(),
) -> PlanDetailOut:
    """Membuat SK lengkap dalam satu transaksi (alur v2) (POST)."""
    return await controller.handle_create_full_plan(current_user, data)


@router.get("", response_model=list[WorkPlanResponse])
async def get_plans(
    status_filter: str | None = None,
    archived: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanController = Depends(),
) -> list[WorkPlanResponse]:
    """Mengambil daftar SK yang terlihat oleh pengguna (V-07) (GET)."""
    return await controller.handle_get_plans(current_user, status_filter, archived)


@router.get("/{plan_id}", response_model=WorkPlanResponse)
async def get_plan(
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanController = Depends(),
) -> WorkPlanResponse:
    """Mengambil data dasar dari sebuah SK (GET)."""
    return await controller.handle_get_plan(access)


@router.get("/{plan_id}/detail", response_model=PlanDetailOut)
async def get_plan_detail(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanController = Depends(),
) -> PlanDetailOut:
    """Mengambil isi lengkap SK: data umum, lokasi, tim, detail pekerjaan per hari, alat & kendaraan (GET)."""
    return await controller.handle_get_plan_detail(access, plan_id)


@router.put("/{plan_id}/full", response_model=PlanDetailOut)
async def edit_full_plan(
    plan_id: UUID,
    data: PlanDraftRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanController = Depends(),
) -> PlanDetailOut:
    """Mengubah seluruh isi SK (draf) dalam satu transaksi (PUT)."""
    return await controller.handle_edit_full_plan(access, plan_id, data)


@router.get("/{plan_id}/preview", response_class=HTMLResponse)
async def preview_plan(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanController = Depends(),
) -> HTMLResponse:
    """Pratinjau A4 draf SK ("Sunting SK", SK2-C) — format sama dengan dokumen terbit (GET)."""
    return await controller.handle_preview_plan(plan_id)


@router.get("/{plan_id}/export", response_class=Response)
async def export_plan(
    plan_id: UUID,
    format: str = Query(default="pdf", pattern="^(pdf|docx|xlsx|pptx)$"),
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanController = Depends(),
) -> Response:
    """Mengunduh rencana kerja dalam berbagai format: PDF, Word (DOCX), Excel (XLSX), PowerPoint (PPTX) (GET)."""
    return await controller.handle_export_plan(plan_id, format, inline=False)


@router.get("/{plan_id}/pdf", response_class=Response)
async def preview_plan_pdf(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanController = Depends(),
) -> Response:
    """Pratinjau PDF langsung di browser (inline) (GET)."""
    return await controller.handle_export_plan(plan_id, "pdf", inline=True)


@router.post("", response_model=WorkPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: WorkPlanCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: WorkPlanController = Depends(),
) -> WorkPlanResponse:
    """Membuat draf rencana kerja (SK) baru (POST)."""
    return await controller.handle_create_plan(current_user, data)


@router.patch("/{plan_id}", response_model=WorkPlanResponse)
async def update_plan(
    plan_id: UUID,
    data: WorkPlanUpdate,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanController = Depends(),
) -> WorkPlanResponse:
    """Mengubah rincian SK berstatus Draf (PATCH). (EDIT_DRAFT, dok 05)"""
    return await controller.handle_update_plan(access, plan_id, data)


@router.post("/{plan_id}/days", response_model=PlanDayResponse)
async def add_day(
    plan_id: UUID,
    data: PlanDayCreate,
    access: PlanAccess = _PM_UNIT_ACCESS,
    controller: WorkPlanController = Depends(),
) -> PlanDayResponse:
    """Menambahkan data hari ke dalam rencana kerja berstatus DRAFT (POST)."""
    return await controller.handle_add_day(access, plan_id, data)


@router.post("/{plan_id}/days/{day_id}/tasks", response_model=PlanTaskResponse)
async def add_task(
    plan_id: UUID,
    day_id: UUID,
    data: PlanTaskCreate,
    access: PlanAccess = _DAY_PM_UNIT_ACCESS,
    controller: WorkPlanController = Depends(),
) -> PlanTaskResponse:
    """Menambahkan tugas baru pada hari tertentu di dalam SK (POST)."""
    return await controller.handle_add_task(day_id, data)


@router.put("/{plan_id}/days/{day_id}/plan")
async def save_day(
    plan_id: UUID,
    day_id: UUID,
    data: DayPlanRequest,
    access: PlanAccess = _DAY_PM_UNIT_ACCESS,
    controller: WorkPlanController = Depends(),
) -> dict[str, object]:
    """Menyusun ulang judul & tugas satu hari selagi SK masih draf (PUT)."""
    return await controller.handle_save_day(access, day_id, data)


@router.post("/items/{item_id}/reschedule", response_model=RescheduleItemResponse)
async def reschedule_item(
    item_id: UUID,
    data: RescheduleItemRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: WorkPlanController = Depends(),
) -> RescheduleItemResponse:
    """Memindahkan atau menjadwalkan ulang item tugas ke hari/slot lain oleh PM (PM Full Override) (POST)."""
    return await controller.handle_reschedule_item(current_user, item_id, data)


__all__ = ["router"]
