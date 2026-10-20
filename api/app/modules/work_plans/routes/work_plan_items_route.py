"""
app/modules/work_plans/routes/work_plan_items_route.py
Endpoint HTTP untuk butir tugas rencana kerja (work_plan_item):
- Pemeriksaan tabrakan jadwal teknisi & armada (conflict detection)
- Pembaruan progres lapangan (actual qty & percent)
- Pengajuan rollover tugas belum selesai
- PM Full Override: persetujuan rollover atau pemindahan slot tugas
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.work_plans.dependencies import get_plan_item_service
from app.modules.work_plans.schemas.plan_item_schema import (
    CheckConflictIn,
    CheckConflictOut,
    GenerateCompletionIn,
    GenerateCompletionOut,
    PmApproveOrMoveIn,
    PmApproveOrMoveOut,
    RequestRolloverIn,
    RequestRolloverOut,
    TaskChainStatusOut,
    UpdateItemProgressIn,
    UpdateItemProgressOut,
)
from app.modules.work_plans.services.plan_item_service import PlanItemService

router = APIRouter(prefix="/work-plans/items", tags=["Work Plan Items & PM Override"])


@router.post("/check-schedule-conflict", response_model=CheckConflictOut)
async def check_schedule_conflict(
    data: CheckConflictIn,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlanItemService = Depends(get_plan_item_service),
) -> CheckConflictOut:
    """Deteksi dini potensi tabrakan jadwal teknisi atau armada pada slot waktu yang sama (POST)."""
    return await service.check_conflicts(data)


@router.patch("/{item_id}/progress", response_model=UpdateItemProgressOut)
async def update_item_progress(
    item_id: UUID,
    data: UpdateItemProgressIn,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlanItemService = Depends(get_plan_item_service),
) -> UpdateItemProgressOut:
    """Memperbarui volume aktual, persentase progres, dan status tugas di lapangan (PATCH)."""
    return await service.update_progress(item_id, data)


@router.post("/{item_id}/request-rollover", response_model=RequestRolloverOut)
async def request_rollover(
    item_id: UUID,
    data: RequestRolloverIn,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlanItemService = Depends(get_plan_item_service),
) -> RequestRolloverOut:
    """Mengajukan rollover tugas yang terkendala ke hari berikutnya menunggu verifikasi PM (POST)."""
    return await service.request_rollover(item_id, data)


@router.post("/{item_id}/pm-approve-or-move", response_model=PmApproveOrMoveOut)
async def pm_approve_or_move(
    item_id: UUID,
    data: PmApproveOrMoveIn,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlanItemService = Depends(get_plan_item_service),
) -> PmApproveOrMoveOut:
    """PM Full Override: Menyetujui rollover, menolak, atau memindahkan slot tugas lintas hari/minggu (POST)."""
    return await service.pm_override_or_approve(current_user, item_id, data)


@router.get("/{item_id}/chain-status", response_model=TaskChainStatusOut)
async def get_task_chain_status(
    item_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlanItemService = Depends(get_plan_item_service),
) -> TaskChainStatusOut:
    """Mengambil status agregasi rantai tugas rollover (task chain) dari awal hingga akhir (GET)."""
    return await service.get_task_chain_status(item_id)


@router.post("/{item_id}/generate-completion", response_model=GenerateCompletionOut)
async def generate_completion_from_chain(
    item_id: UUID,
    payload: GenerateCompletionIn | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlanItemService = Depends(get_plan_item_service),
) -> GenerateCompletionOut:
    """Mengompilasi seluruh rantai tugas 100% selesai menjadi Berita Acara Work Completion (POST)."""
    c_name = payload.client_name if payload else None
    p_title = payload.project_title if payload else None
    return await service.generate_completion_from_chain(
        item_id=item_id,
        current_user=current_user,
        client_name=c_name,
        project_title=p_title,
    )


__all__ = ["router"]

