"""Baca hari kerja SK: tugas + laporan harian per hari (untuk layar laporan harian web/mobile)."""
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_plan_day_service, plan_access
from app.schemas.plan_day import PlanDayOut
from app.services.access_service import PlanAccess, PlanNeed
from app.services.plan_day_service import PlanDayService

router = APIRouter(prefix="/work-plans/{plan_id}/days", tags=["Daily Reports"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))








def _out(row: Any) -> PlanDayOut:
    """
    Fungsi pembantu untuk memetakan row data hari kerja dari database ke skema PlanDayOut.
    
    Args:
        row (Any): Row data hari kerja.
        
    Returns:
        PlanDayOut: Respons model hari kerja SK.
    """
    return PlanDayOut(**row._mapping)


@router.get("", response_model=list[PlanDayOut])
async def list_plan_days(access: PlanAccess = _VIEW_ACCESS,
                         plan_day_service: PlanDayService = Depends(get_plan_day_service)) -> list[PlanDayOut]:
    """
    Mengambil daftar hari kerja beserta tugas dan laporan harian dari SK (GET).
    Siapa pun yang melihat SK (V-07); SK tak terlihat / organisasi lain → 404.
    
    Path Parameters:
    - plan_id (tersirat via router prefix): ID SK bersangkutan.
    
    Returns:
    - list[PlanDayOut]: Daftar detail hari kerja SK.
    """
    # Menggunakan Dependency Injection untuk kontrol visibilitas plan (_VIEW_ACCESS)
    # Memanggil service layer untuk mengambil data hari kerja
    return [_out(row) for row in await plan_day_service.list_days(access)]
