"""
app/modules/units/routes/unit_route.py

Rute endpoint HTTP untuk unit organisasi (/units).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.units.controllers.unit_controller import UnitController
from app.modules.units.schemas.unit_schema import UnitOut

router = APIRouter(prefix="/units", tags=["Units"])


@router.get("", response_model=list[UnitOut])
async def list_units(
    current_user: CurrentUser = Depends(get_current_user),
    controller: UnitController = Depends(),
) -> list[UnitOut]:
    """
    Mengambil daftar unit milik organisasi pengguna saat ini.
    """
    return await controller.handle_list_units(current_user.organization_id)

