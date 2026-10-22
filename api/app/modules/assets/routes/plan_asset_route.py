"""
app/modules/assets/routes/plan_asset_route.py

Aset yang dipinjam untuk satu jadwal harian (/work-plans/daily/{daily_plan_id}/assets) — untuk HP ketua tim.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.assets.controllers.asset_controller import AssetController
from app.modules.assets.schemas.asset_schema import LoanOut

plan_assets_router = APIRouter(prefix="/work-plans/daily/{daily_plan_id}", tags=["Assets"])


@plan_assets_router.get("/assets", response_model=list[LoanOut])
async def get_plan_assets(
    daily_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: AssetController = Depends(),
) -> list[LoanOut]:
    """Peminjaman aset yang dikaitkan ke jadwal harian ini (anggota tim melihat semuanya)."""
    return await controller.handle_loans(current_user, open_only=False, employee_id=None, daily_plan_id=daily_plan_id)
