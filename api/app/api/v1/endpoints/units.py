"""Daftar unit organisasi (R-19: pilihan unit mutasi/promosi). Tipis: SQL di crud/crud_unit.py."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_unit_service
from app.core.security import CurrentUser
from app.schemas.unit import UnitOut
from app.services.unit_service import UnitService

router = APIRouter(prefix="/units", tags=["Units"])




@router.get("", response_model=list[UnitOut])
async def list_units(
    current_user: CurrentUser = Depends(get_current_user),
    unit_service: UnitService = Depends(get_unit_service),
) -> list[UnitOut]:
    """Unit milik organisasi pengguna saja (V-09)."""
    return [UnitOut(**r._mapping) for r in await unit_service.list_units(current_user.organization_id)]
