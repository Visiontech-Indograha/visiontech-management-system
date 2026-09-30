"""Daftar unit organisasi (R-19: pilihan unit mutasi/promosi). Tipis: SQL di crud/crud_unit.py."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user
from app.crud.crud_unit import CRUDUnit
from app.schemas.unit import UnitOut
from app.services.unit_service import UnitService

router = APIRouter(prefix="/units", tags=["Units"])




@router.get("", response_model=list[UnitOut])
async def list_units(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> list[UnitOut]:
    """Unit milik organisasi pengguna saja (V-09)."""
    return [UnitOut(**r._mapping) for r in await UnitService(CRUDUnit(db)).list_units(current_user.organization_id)]
