"""
app/modules/work_plans/routes/work_plan_v2_route.py

Rute endpoint HTTP untuk manajemen Rencana Kerja V2 terintegrasi:
- Form Options V2 (/work-plans/form-options-v2)
- CRUD Rencana Mingguan (/work-plans/weekly)
- CRUD Hari Kerja (/work-plans/daily)
- CRUD Butir Tugas (/work-plans/items)
Mengikuti Standar Arsitektur API FastAPI Modular VMS & Master Schema V2.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.work_plans.controllers.work_plan_v2_controller import WorkPlanV2Controller
from app.modules.work_plans.schemas.work_plan_v2_schema import (
    BulkApproveDailyPlansIn,
    BulkApproveDailyPlansOut,
    DailyPlanCreateIn,
    DailyPlanOut,
    DailyPlanUpdateIn,
    PlanItemCreateIn,
    PlanItemOut,
    PlanItemUpdateIn,
    ProjectScheduleOut,
    WeeklyCalendarMatrixOut,
    WeeklyPlanCreateIn,
    WeeklyPlanDetailOut,
    WeeklyPlanListOut,
    WeeklyPlanUpdateIn,
    WorkPlanFormOptionsV2Out,
)

router = APIRouter(tags=["Work Plan V2"])


# ── FORM OPTIONS V2 ──────────────────────────────────────────


@router.get("/work-plans/form-options-v2", response_model=WorkPlanFormOptionsV2Out)
async def get_work_plan_form_options_v2(
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> WorkPlanFormOptionsV2Out:
    """Mengambil seluruh data referensi dropdown master untuk form Rencana Kerja V2."""
    return await controller.handle_form_options()


# ── WEEKLY MATRIX & PROJECT SCHEDULE (DAILY-FIRST) ───────────


@router.get("/work-plans/matrix", response_model=WeeklyCalendarMatrixOut)
async def get_weekly_matrix(
    start_date: date = Query(..., description="Tanggal awal rentang minggu (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Tanggal akhir rentang minggu (YYYY-MM-DD)"),
    division_id: UUID | None = Query(None),
    team_id: UUID | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> WeeklyCalendarMatrixOut:
    """Mengambil matriks kalender harian (Daily-First) untuk seluruh hari dalam rentang tanggal."""
    return await controller.handle_weekly_matrix(start_date, end_date, division_id, team_id)


@router.post("/work-plans/matrix/bulk-approve", response_model=BulkApproveDailyPlansOut)
async def bulk_approve_weekly_matrix(
    payload: BulkApproveDailyPlansIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> BulkApproveDailyPlansOut:
    """Persetujuan serentak oleh Project Manager untuk jadwal satu minggu kerja tim."""
    return await controller.handle_bulk_approve(current_user, payload)


@router.get("/work-plans/project/{completion_id}/schedule", response_model=ProjectScheduleOut)
async def get_project_schedule(
    completion_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> ProjectScheduleOut:
    """Mengambil linimasa jadwal proyek multi-minggu (CCTV Site A dsb.) beserta rekap tahapan dan deliverable."""
    return await controller.handle_project_schedule(completion_id)


# ── WEEKLY PLAN CRUD ─────────────────────────────────────────


@router.get("/work-plans/weekly", response_model=list[WeeklyPlanListOut])
async def list_weekly_plans_v2(
    status_filter: str | None = Query(None, alias="status"),
    division_id: UUID | None = Query(None),
    team_id: UUID | None = Query(None),
    year: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> list[WeeklyPlanListOut]:
    """Mengambil daftar ringkas rencana kerja mingguan dengan filter."""
    return await controller.handle_list_weekly(status_filter, division_id, team_id, year, limit)


@router.get("/work-plans/weekly/{weekly_plan_id}", response_model=WeeklyPlanDetailOut)
async def get_weekly_plan_detail_v2(
    weekly_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> WeeklyPlanDetailOut:
    """Mengambil rincian lengkap rencana kerja mingguan beserta hari dan item tugas."""
    return await controller.handle_weekly_detail(weekly_plan_id)


@router.post(
    "/work-plans/weekly",
    response_model=WeeklyPlanDetailOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_weekly_plan_v2(
    payload: WeeklyPlanCreateIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> WeeklyPlanDetailOut:
    """Membuat rencana kerja mingguan baru (dapat mencakup hari & butir tugas bertingkat)."""
    return await controller.handle_create_weekly(current_user, payload)


@router.put("/work-plans/weekly/{weekly_plan_id}", response_model=WeeklyPlanDetailOut)
async def update_weekly_plan_v2(
    weekly_plan_id: UUID,
    payload: WeeklyPlanUpdateIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> WeeklyPlanDetailOut:
    """Memperbarui rencana kerja mingguan."""
    return await controller.handle_update_weekly(weekly_plan_id, payload)


@router.delete("/work-plans/weekly/{weekly_plan_id}")
async def delete_weekly_plan_v2(
    weekly_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> dict[str, str]:
    """Menghapus (soft delete) rencana kerja mingguan beserta seluruh hari dan tugas terkait."""
    return await controller.handle_delete_weekly(weekly_plan_id)


# ── DAILY PLAN CRUD ──────────────────────────────────────────


@router.get("/work-plans/daily/{daily_plan_id}", response_model=DailyPlanOut)
async def get_daily_plan_v2(
    daily_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> DailyPlanOut:
    """Mengambil data hari kerja beserta seluruh slot tugas pada tanggal tersebut."""
    return await controller.handle_daily(daily_plan_id)


@router.post(
    "/work-plans/daily",
    response_model=DailyPlanOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_daily_plan_v2(
    payload: DailyPlanCreateIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> DailyPlanOut:
    """Menambahkan hari kerja baru langsung ke dalam sistem."""
    return await controller.handle_create_daily(current_user, payload)


@router.put("/work-plans/daily/{daily_plan_id}", response_model=DailyPlanOut)
async def update_daily_plan_v2(
    daily_plan_id: UUID,
    payload: DailyPlanUpdateIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> DailyPlanOut:
    """Memperbarui informasi hari kerja (lokasi, jam kerja, radius absensi, hari libur)."""
    return await controller.handle_update_daily(daily_plan_id, payload)


@router.delete("/work-plans/daily/{daily_plan_id}")
async def delete_daily_plan_v2(
    daily_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> dict[str, str]:
    """Menghapus (soft delete) hari kerja beserta tugas-tugas di dalamnya."""
    return await controller.handle_delete_daily(daily_plan_id)


# ── PLAN ITEM CRUD ───────────────────────────────────────────


@router.get("/work-plans/items/{item_id}", response_model=PlanItemOut)
async def get_plan_item_v2(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> PlanItemOut:
    """Mengambil rincian data satu butir tugas pekerjaan."""
    return await controller.handle_item(item_id)


@router.post(
    "/work-plans/items",
    response_model=PlanItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_plan_item_v2(
    payload: PlanItemCreateIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> PlanItemOut:
    """Menambahkan slot butir tugas baru ke dalam hari kerja tertentu."""
    return await controller.handle_create_item(payload)


@router.put("/work-plans/items/{item_id}", response_model=PlanItemOut)
async def update_plan_item_v2(
    item_id: UUID,
    payload: PlanItemUpdateIn,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> PlanItemOut:
    """Memperbarui informasi butir tugas (volume, jam slot, status, teknisi pelaksana)."""
    return await controller.handle_update_item(item_id, payload)


@router.delete("/work-plans/items/{item_id}")
async def delete_plan_item_v2(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkPlanV2Controller = Depends(),
) -> dict[str, str]:
    """Menghapus (soft delete) satu butir tugas dari jadwal hari kerja."""
    return await controller.handle_delete_item(item_id)
