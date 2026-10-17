"""
app/modules/sites/routes/site_route.py

Rute endpoint HTTP untuk lokasi kerja (/sites).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.sites.controllers.site_controller import SiteController
from app.modules.sites.schemas.site_schema import SiteCreate, SiteResponse

router = APIRouter(prefix="/sites", tags=["Sites"])


@router.get("", response_model=list[SiteResponse])
async def get_sites(
    for_attendance: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    controller: SiteController = Depends(),
) -> list[SiteResponse]:
    """
    Mengambil daftar lokasi kerja (GET).
    """
    return await controller.handle_list_sites(current_user, for_attendance)


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    data: SiteCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_SITES)),
    controller: SiteController = Depends(),
) -> SiteResponse:
    """
    Membuat lokasi kerja baru (POST).
    """
    return await controller.handle_create_site(current_user, data)


@router.delete("/{site_id}")
async def delete_site(
    site_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_SITES)),
    controller: SiteController = Depends(),
) -> dict[str, str]:
    """
    Menghapus lokasi kerja berdasarkan ID-nya (DELETE).
    """
    return await controller.handle_delete_site(current_user, site_id)
