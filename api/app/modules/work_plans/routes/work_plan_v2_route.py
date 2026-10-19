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

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.errors import NotFoundError
from app.core.security import CurrentUser
from app.crud.crud_work_plan_v2 import CRUDWorkPlanV2
from app.modules.work_plans.schemas.work_plan_v2_schema import (
    DailyPlanCreateIn,
    DailyPlanOut,
    DailyPlanUpdateIn,
    PlanItemCreateIn,
    PlanItemOut,
    PlanItemUpdateIn,
    WeeklyPlanCreateIn,
    WeeklyPlanDetailOut,
    WeeklyPlanListOut,
    WeeklyPlanUpdateIn,
    WorkPlanFormOptionsV2Out,
)

router = APIRouter(tags=["Work Plan V2"])


async def get_crud_work_plan_v2(db: AsyncSession = Depends(get_db)) -> CRUDWorkPlanV2:
    """Dependency injection untuk instance CRUDWorkPlanV2."""
    return CRUDWorkPlanV2(db)


# ── FORM OPTIONS V2 ──────────────────────────────────────────


@router.get("/work-plans/form-options-v2", response_model=WorkPlanFormOptionsV2Out)
async def get_work_plan_form_options_v2(
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> WorkPlanFormOptionsV2Out:
    """Mengambil seluruh data referensi dropdown master untuk form Rencana Kerja V2."""
    return await crud.get_form_options_v2()


# ── WEEKLY PLAN CRUD ─────────────────────────────────────────


@router.get("/work-plans/weekly", response_model=list[WeeklyPlanListOut])
async def list_weekly_plans_v2(
    status_filter: str | None = Query(None, alias="status"),
    division_id: UUID | None = Query(None),
    team_id: UUID | None = Query(None),
    year: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> list[WeeklyPlanListOut]:
    """Mengambil daftar ringkas rencana kerja mingguan dengan filter."""
    return await crud.list_weekly_plans(
        status_filter=status_filter,
        division_id=division_id,
        team_id=team_id,
        year=year,
        limit=limit,
    )


@router.get("/work-plans/weekly/{weekly_plan_id}", response_model=WeeklyPlanDetailOut)
async def get_weekly_plan_detail_v2(
    weekly_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> WeeklyPlanDetailOut:
    """Mengambil rincian lengkap rencana kerja mingguan beserta hari dan item tugas."""
    plan = await crud.get_weekly_plan_detail(weekly_plan_id)
    if not plan:
        raise NotFoundError("Rencana kerja mingguan tidak ditemukan.")
    return plan


@router.post(
    "/work-plans/weekly",
    response_model=WeeklyPlanDetailOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_weekly_plan_v2(
    payload: WeeklyPlanCreateIn,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> WeeklyPlanDetailOut:
    """Membuat rencana kerja mingguan baru (dapat mencakup hari & butir tugas bertingkat)."""
    creator_id = await crud.get_creator_employee_id(current_user.user_id)
    return await crud.create_weekly_plan(creator_id, payload)


@router.put("/work-plans/weekly/{weekly_plan_id}", response_model=WeeklyPlanDetailOut)
async def update_weekly_plan_v2(
    weekly_plan_id: UUID,
    payload: WeeklyPlanUpdateIn,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> WeeklyPlanDetailOut:
    """Memperbarui rencana kerja mingguan."""
    plan = await crud.update_weekly_plan(weekly_plan_id, payload)
    if not plan:
        raise NotFoundError("Rencana kerja mingguan tidak ditemukan.")
    return plan


@router.delete("/work-plans/weekly/{weekly_plan_id}")
async def delete_weekly_plan_v2(
    weekly_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> dict[str, str]:
    """Menghapus (soft delete) rencana kerja mingguan beserta seluruh hari dan tugas terkait."""
    deleted = await crud.delete_weekly_plan(weekly_plan_id)
    if not deleted:
        raise NotFoundError("Rencana kerja mingguan tidak ditemukan atau telah dihapus.")
    return {"message": "Rencana kerja mingguan berhasil dihapus."}


# ── DAILY PLAN CRUD ──────────────────────────────────────────


@router.get("/work-plans/daily/{daily_plan_id}", response_model=DailyPlanOut)
async def get_daily_plan_v2(
    daily_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> DailyPlanOut:
    """Mengambil data hari kerja beserta seluruh slot tugas pada tanggal tersebut."""
    day = await crud.get_daily_plan(daily_plan_id)
    if not day:
        raise NotFoundError("Hari kerja tidak ditemukan.")
    return day


@router.post(
    "/work-plans/daily",
    response_model=DailyPlanOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_daily_plan_v2(
    payload: DailyPlanCreateIn,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> DailyPlanOut:
    """Menambahkan hari kerja baru ke dalam rencana mingguan."""
    return await crud.create_daily_plan(payload)


@router.put("/work-plans/daily/{daily_plan_id}", response_model=DailyPlanOut)
async def update_daily_plan_v2(
    daily_plan_id: UUID,
    payload: DailyPlanUpdateIn,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> DailyPlanOut:
    """Memperbarui informasi hari kerja (lokasi, jam kerja, radius absensi, hari libur)."""
    day = await crud.update_daily_plan(daily_plan_id, payload)
    if not day:
        raise NotFoundError("Hari kerja tidak ditemukan.")
    return day


@router.delete("/work-plans/daily/{daily_plan_id}")
async def delete_daily_plan_v2(
    daily_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> dict[str, str]:
    """Menghapus (soft delete) hari kerja beserta tugas-tugas di dalamnya."""
    deleted = await crud.delete_daily_plan(daily_plan_id)
    if not deleted:
        raise NotFoundError("Hari kerja tidak ditemukan atau telah dihapus.")
    return {"message": "Hari kerja berhasil dihapus."}


# ── PLAN ITEM CRUD ───────────────────────────────────────────


@router.get("/work-plans/items/{item_id}", response_model=PlanItemOut)
async def get_plan_item_v2(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> PlanItemOut:
    """Mengambil rincian data satu butir tugas pekerjaan."""
    item = await crud.get_plan_item(item_id)
    if not item:
        raise NotFoundError("Butir tugas tidak ditemukan.")
    return item


@router.post(
    "/work-plans/items",
    response_model=PlanItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_plan_item_v2(
    payload: PlanItemCreateIn,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> PlanItemOut:
    """Menambahkan slot butir tugas baru ke dalam hari kerja tertentu."""
    return await crud.create_plan_item(payload)


@router.put("/work-plans/items/{item_id}", response_model=PlanItemOut)
async def update_plan_item_v2(
    item_id: UUID,
    payload: PlanItemUpdateIn,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> PlanItemOut:
    """Memperbarui informasi butir tugas (volume, jam slot, status, teknisi pelaksana)."""
    item = await crud.update_plan_item(item_id, payload)
    if not item:
        raise NotFoundError("Butir tugas tidak ditemukan.")
    return item


@router.delete("/work-plans/items/{item_id}")
async def delete_plan_item_v2(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    crud: CRUDWorkPlanV2 = Depends(get_crud_work_plan_v2),
) -> dict[str, str]:
    """Menghapus (soft delete) satu butir tugas dari jadwal hari kerja."""
    deleted = await crud.delete_plan_item(item_id)
    if not deleted:
        raise NotFoundError("Butir tugas tidak ditemukan atau telah dihapus.")
    return {"message": "Butir tugas berhasil dihapus."}
