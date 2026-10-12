"""
app/modules/assets/routes/plan_asset_route.py

Rute endpoint HTTP untuk aset yang terkait dengan SK (/work-plans/{plan_id}/assets).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import plan_access
from app.modules.assets.controllers.asset_controller import AssetController
from app.modules.assets.schemas.asset_schema import PlanAssetItem
from app.services.access_service import PlanAccess, PlanNeed

plan_assets_router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Assets"])
_PLAN_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))


@plan_assets_router.get("/assets", response_model=list[PlanAssetItem])
async def get_plan_assets(
    plan_id: UUID,
    access: PlanAccess = _PLAN_VIEW_ACCESS,
    controller: AssetController = Depends(),
) -> list[PlanAssetItem]:
    """Aset yang dipakai SK beserta kondisi saat dikembalikan."""
    return await controller.handle_plan_assets(plan_id)
