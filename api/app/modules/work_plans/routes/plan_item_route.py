"""
app/modules/work_plans/routes/plan_item_route.py
Rute item pekerjaan per titik (Milestone 6): susun item di jadwal (PM/OM divisi), progres & foto (tim), rollover
(ketua ajukan, PM putuskan), rantai rollover. Kedudukan pada jadwal diperiksa di service (check_daily_access).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.work_plans.controllers.plan_item_controller import PlanItemController
from app.modules.work_plans.schemas.plan_item_schema import (
    ChainStep,
    PlanItemCreate,
    PlanItemOut,
    PlanItemUpdate,
    ProgressIn,
    RolloverDecision,
    RolloverRequest,
)

router = APIRouter(prefix="/work-plans", tags=["Work Plan Items"])
_LOGIN = Depends(get_current_user)
_PLANNER = Depends(require_permission(Permission.CREATE_PLAN))


@router.get("/daily/{daily_plan_id}/items", response_model=list[PlanItemOut])
async def list_items(daily_plan_id: UUID, current_user: CurrentUser = _LOGIN,
                     controller: PlanItemController = Depends()) -> list[PlanItemOut]:
    """Item jadwal harian (siapa pun yang boleh melihat jadwal itu)."""
    return await controller.handle_list(current_user, daily_plan_id)


@router.post("/daily/{daily_plan_id}/items", response_model=PlanItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(daily_plan_id: UUID, data: PlanItemCreate, current_user: CurrentUser = _PLANNER,
                      controller: PlanItemController = Depends()) -> PlanItemOut:
    """Tambah item per titik (jadwal DRAFT/SUBMITTED)."""
    return await controller.handle_create(current_user, daily_plan_id, data)


@router.get("/items/{item_id}", response_model=PlanItemOut)
async def get_item(item_id: UUID, current_user: CurrentUser = _LOGIN,
                   controller: PlanItemController = Depends()) -> PlanItemOut:
    """Detail item."""
    return await controller.handle_get(current_user, item_id)


@router.put("/items/{item_id}", response_model=PlanItemOut)
async def update_item(item_id: UUID, data: PlanItemUpdate, current_user: CurrentUser = _PLANNER,
                      controller: PlanItemController = Depends()) -> PlanItemOut:
    """Ubah item (jadwal DRAFT/SUBMITTED)."""
    return await controller.handle_update(current_user, item_id, data)


@router.delete("/items/{item_id}")
async def delete_item(item_id: UUID, current_user: CurrentUser = _PLANNER,
                      controller: PlanItemController = Depends()) -> dict[str, str]:
    """Hapus item yang bukan prasyarat item lain (jadwal DRAFT/SUBMITTED)."""
    return await controller.handle_delete(current_user, item_id)


@router.patch("/items/{item_id}/progress", response_model=PlanItemOut)
async def update_progress(item_id: UUID, data: ProgressIn, current_user: CurrentUser = _LOGIN,
                          controller: PlanItemController = Depends()) -> PlanItemOut:
    """Tim mencatat volume selesai & foto realisasi (jadwal ONGOING; prasyarat harus selesai)."""
    return await controller.handle_progress(current_user, item_id, data)


@router.post("/items/{item_id}/request-rollover", response_model=PlanItemOut)
async def request_rollover(item_id: UUID, data: RolloverRequest, current_user: CurrentUser = _LOGIN,
                           controller: PlanItemController = Depends()) -> PlanItemOut:
    """Ketua mengajukan geser item yang belum selesai (alasan + progres parsial)."""
    return await controller.handle_request_rollover(current_user, item_id, data)


@router.post("/items/{item_id}/rollover-decision", response_model=PlanItemOut)
async def decide_rollover(item_id: UUID, data: RolloverDecision, current_user: CurrentUser = _PLANNER,
                          controller: PlanItemController = Depends()) -> PlanItemOut:
    """PM/OM divisi: setujui (ke jadwal yang ada / tanggal baru) → item lanjutan; atau tolak."""
    return await controller.handle_decide_rollover(current_user, item_id, data)


@router.get("/items/{item_id}/chain", response_model=list[ChainStep])
async def rollover_chain(item_id: UUID, current_user: CurrentUser = _LOGIN,
                         controller: PlanItemController = Depends()) -> list[ChainStep]:
    """Rantai rollover item (asal pertama → item aktif terakhir)."""
    return await controller.handle_chain(current_user, item_id)
