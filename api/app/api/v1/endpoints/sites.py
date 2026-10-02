"""
Lokasi kerja. Tipis (dok 12 §2): aturan di services/site_service.py (R-33), SQL di crud/crud_site.py.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_site_service, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.attendance import GeoPoint, SiteCreate, SiteResponse
from app.services.site_service import SiteService

router = APIRouter(prefix="/sites", tags=["Sites"])


def _response(r: Any, can_manage: bool = False) -> SiteResponse:
    return SiteResponse(id=r.id, name=r.name, address=r.address, radius_m=r.radius_m or 50,
                        unit_id=r.unit_id, can_manage=can_manage, location=GeoPoint(lat=r.lat, lng=r.lng))


@router.get("", response_model=list[SiteResponse])
async def get_sites(
    for_attendance: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    site_service: SiteService = Depends(get_site_service),
) -> list[SiteResponse]:
    """R-33: lapangan → lokasi unitnya; kantor → lokasi kantor; PM → kantor + unitnya; OPS → semua.
    `for_attendance=true`: hanya lokasi yang sah untuk absen peminta. `can_manage`: boleh dihapus peminta."""
    manager, unit = await site_service.manageable(current_user)
    rows = await site_service.list_sites(current_user, for_attendance=for_attendance)
    return [_response(r, manager and r.unit_id == unit) for r in rows]


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    data: SiteCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_SITES)),
    site_service: SiteService = Depends(get_site_service),
) -> SiteResponse:
    """R-33: PM → lokasi proyek unitnya (untuk bawahannya); Finance → lokasi kantor. Unit ditetapkan server."""
    row = await site_service.create_site(current_user, name=data.name, address=data.address,
                                         radius_m=data.radius_m, lat=data.location.lat, lng=data.location.lng)
    return _response(row, True)


@router.delete("/{site_id}")
async def delete_site(
    site_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_SITES)),
    site_service: SiteService = Depends(get_site_service),
) -> dict[str, str]:
    await site_service.delete_site(current_user, site_id)
    return {"message": "Lokasi dihapus."}
