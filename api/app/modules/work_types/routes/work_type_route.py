"""
app/modules/work_types/routes/work_type_route.py

Rute endpoint HTTP untuk jenis pekerjaan (/work-types dan /work-plans/{plan_id}/photo-template).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_user, plan_access, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.work_types.controllers.work_type_controller import WorkTypeController
from app.modules.work_types.schemas.work_type_schema import WorkTypeIn, WorkTypeOut, WorkTypePhotoOut
from app.services.access_service import PlanAccess, PlanNeed

router = APIRouter(tags=["Work Types"])
_MANAGE = Depends(require_permission(Permission.CREATE_PLAN))
_VIEW = Depends(plan_access(PlanNeed.VIEW))


@router.get("/work-types", response_model=list[WorkTypeOut])
async def list_work_types(
    all: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkTypeController = Depends(),
) -> list[WorkTypeOut]:
    """
    Daftar jenis pekerjaan beserta template foto (GET).
    """
    include_inactive = all and Permission.CREATE_PLAN in current_user.permissions
    return await controller.handle_list_types(current_user.organization_id, include_inactive)


@router.post("/work-types", response_model=WorkTypeOut, status_code=status.HTTP_201_CREATED)
async def create_work_type(
    data: WorkTypeIn,
    current_user: CurrentUser = _MANAGE,
    controller: WorkTypeController = Depends(),
) -> WorkTypeOut:
    """
    Membuat jenis pekerjaan baru beserta template foto.
    """
    return await controller.handle_create(current_user.organization_id, data)


@router.put("/work-types/{type_id}", response_model=WorkTypeOut)
async def update_work_type(
    type_id: UUID,
    data: WorkTypeIn,
    current_user: CurrentUser = _MANAGE,
    controller: WorkTypeController = Depends(),
) -> WorkTypeOut:
    """
    Mengubah nama dan mengganti seluruh daftar slot foto jenis pekerjaan.
    """
    return await controller.handle_update(current_user.organization_id, type_id, data)


@router.delete("/work-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_work_type(
    type_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: WorkTypeController = Depends(),
) -> Response:
    """
    Menonaktifkan jenis pekerjaan.
    """
    await controller.handle_deactivate(current_user.organization_id, type_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/work-plans/{plan_id}/photo-template", response_model=list[WorkTypePhotoOut])
async def plan_photo_template(
    plan_id: UUID,
    day_id: UUID | None = None,
    access: PlanAccess = _VIEW,
    controller: WorkTypeController = Depends(),
) -> list[WorkTypePhotoOut]:
    """
    Template foto laporan rencana kerja.
    """
    return await controller.handle_template_of_plan(plan_id, day_id)
