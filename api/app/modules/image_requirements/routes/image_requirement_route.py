"""
app/modules/image_requirements/routes/image_requirement_route.py
Rute API HTTP untuk pengelolaan persyaratan foto wajib dokumentasi lapangan.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.image_requirements.controllers.image_requirement_controller import ImageRequirementController
from app.modules.image_requirements.schemas.image_requirement_schema import (
    ImageRequirementCreate,
    ImageRequirementOut,
    ImageRequirementUpdate,
)

router = APIRouter(prefix="/image-requirements", tags=["Image Requirements"])
_MANAGE = Depends(require_permission(Permission.MANAGE_IMAGE_REQUIREMENTS))


@router.get("/by-work-type/{work_type_id}", response_model=list[ImageRequirementOut])
async def list_by_work_type(
    work_type_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ImageRequirementController = Depends(),
) -> list[ImageRequirementOut]:
    """Mengambil daftar persyaratan foto dokumentasi untuk jenis pekerjaan tertentu."""
    return await controller.handle_list_by_work_type(current_user, work_type_id)


@router.get("/{requirement_id}", response_model=ImageRequirementOut)
async def get_by_id(
    requirement_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ImageRequirementController = Depends(),
) -> ImageRequirementOut:
    """Mengambil detail persyaratan foto dokumentasi."""
    return await controller.handle_get_by_id(current_user, requirement_id)


@router.post("", response_model=ImageRequirementOut, status_code=201)
async def create_requirement(
    data: ImageRequirementCreate,
    current_user: CurrentUser = _MANAGE,
    controller: ImageRequirementController = Depends(),
) -> ImageRequirementOut:
    """Menambahkan persyaratan foto wajib dokumentasi lapangan."""
    return await controller.handle_create(current_user, data)


@router.put("/{requirement_id}", response_model=ImageRequirementOut)
async def update_requirement(
    requirement_id: UUID,
    data: ImageRequirementUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: ImageRequirementController = Depends(),
) -> ImageRequirementOut:
    """Memperbarui informasi persyaratan foto."""
    return await controller.handle_update(current_user, requirement_id, data)


@router.delete("/{requirement_id}")
async def delete_requirement(
    requirement_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: ImageRequirementController = Depends(),
) -> dict[str, str]:
    """Menghapus persyaratan foto dokumentasi."""
    return await controller.handle_delete(current_user, requirement_id)
