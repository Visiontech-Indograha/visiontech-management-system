"""
app/modules/work_types/routes/work_type_route.py

Rute endpoint HTTP untuk jenis pekerjaan (/work-types dan /work-plans/{plan_id}/photo-template).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import daily_access, get_current_user, require_permission
from app.core.list_params import ListParams, apply_list
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.work_types.controllers.work_type_controller import WorkTypeController
from app.modules.work_types.schemas.work_type_schema import (
    DefaultMaterialIn,
    DefaultMaterialOut,
    DefaultMaterialUpdate,
    WorkTypeIn,
    WorkTypeOut,
    WorkTypePhotoOut,
)
from app.shared.access.access_service import DailyAccess, DailyNeed

router = APIRouter(tags=["Work Types"])
_MANAGE = Depends(require_permission(Permission.CREATE_PLAN))
_VIEW = Depends(daily_access(DailyNeed.VIEW))


@router.get("/work-types", response_model=list[WorkTypeOut])
async def list_work_types(
    response: Response,
    params: ListParams = Depends(),
    all: bool = False,
    division_id: UUID | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkTypeController = Depends(),
) -> list[WorkTypeOut]:
    """
    Daftar jenis pekerjaan beserta template foto (GET).
    Jika pengguna adalah Project Manager, daftar otomatis difilter ke divisi miliknya.
    """
    include_inactive = all and Permission.CREATE_PLAN in current_user.permissions
    user_divs = await controller.get_user_divisions(current_user.user_id)

    # Pembatasan: PM (dan peran lapangan berdivisi) hanya melihat work type di divisi-divisinya.
    targets: list[UUID] | None
    if current_user.role == "PROJECT_MANAGER" or (
        user_divs and current_user.role not in ("SUPER_ADMIN", "ADMIN", "OPERATIONAL_MANAGER")
    ):
        targets = [d for d in user_divs if division_id is None or d == division_id]
    else:
        targets = [division_id] if division_id else None

    rows = await controller.handle_list_types(current_user.organization_id, include_inactive, targets)
    return list(apply_list(rows, params, response, lambda t: (t.name, t.division_name, t.description)))


@router.post("/work-types", response_model=WorkTypeOut, status_code=status.HTTP_201_CREATED)
async def create_work_type(
    data: WorkTypeIn,
    current_user: CurrentUser = _MANAGE,
    controller: WorkTypeController = Depends(),
) -> WorkTypeOut:
    """
    Membuat jenis pekerjaan baru beserta template foto.
    PM hanya dapat membuat work type di dalam divisinya sendiri.
    """
    user_divs = await controller.get_user_divisions(current_user.user_id)
    creator_div = user_divs if current_user.role == "PROJECT_MANAGER" else None
    if not data.division_id and len(user_divs) == 1:
        data.division_id = user_divs[0]
    return await controller.handle_create(current_user.organization_id, data, creator_div)


@router.put("/work-types/{type_id}", response_model=WorkTypeOut)
async def update_work_type(
    type_id: UUID,
    data: WorkTypeIn,
    current_user: CurrentUser = _MANAGE,
    controller: WorkTypeController = Depends(),
) -> WorkTypeOut:
    """
    Mengubah nama dan mengganti seluruh daftar slot foto jenis pekerjaan.
    PM hanya dapat mengubah work type di dalam divisinya sendiri.
    """
    user_divs = await controller.get_user_divisions(current_user.user_id)
    creator_div = user_divs if current_user.role == "PROJECT_MANAGER" else None
    if not data.division_id and len(user_divs) == 1:
        data.division_id = user_divs[0]
    return await controller.handle_update(current_user.organization_id, type_id, data, creator_div)


@router.delete("/work-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_work_type(
    type_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: WorkTypeController = Depends(),
) -> Response:
    """
    Menonaktifkan jenis pekerjaan.
    PM hanya dapat menonaktifkan work type di dalam divisinya sendiri.
    """
    user_divs = await controller.get_user_divisions(current_user.user_id)
    creator_div = user_divs if current_user.role == "PROJECT_MANAGER" else None
    await controller.handle_deactivate(current_user.organization_id, type_id, creator_div)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/work-plans/daily/{daily_plan_id}/photo-template", response_model=list[WorkTypePhotoOut])
async def plan_photo_template(
    daily_plan_id: UUID,
    access: DailyAccess = _VIEW,
    controller: WorkTypeController = Depends(),
) -> list[WorkTypePhotoOut]:
    """
    Template foto SOP untuk item-item jadwal harian ini.
    """
    return await controller.handle_template_of_daily(daily_plan_id)


@router.get("/work-types/{type_id}/materials", response_model=list[DefaultMaterialOut])
async def list_work_type_materials(
    type_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: WorkTypeController = Depends(),
) -> list[DefaultMaterialOut]:
    """
    Daftar template material default untuk jenis pekerjaan tertentu.
    """
    return await controller.handle_list_materials(current_user.organization_id, type_id)


@router.post(
    "/work-types/{type_id}/materials",
    response_model=DefaultMaterialOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_work_type_material(
    type_id: UUID,
    data: DefaultMaterialIn,
    current_user: CurrentUser = _MANAGE,
    controller: WorkTypeController = Depends(),
) -> DefaultMaterialOut:
    """
    Menambahkan template material default baru ke jenis pekerjaan.
    """
    user_divs = await controller.get_user_divisions(current_user.user_id)
    creator_div = user_divs if current_user.role == "PROJECT_MANAGER" else None
    return await controller.handle_create_material(current_user.organization_id, type_id, data, creator_div)


@router.put("/work-types/materials/{material_id}", response_model=DefaultMaterialOut)
async def update_work_type_material(
    material_id: UUID,
    data: DefaultMaterialUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: WorkTypeController = Depends(),
) -> DefaultMaterialOut:
    """
    Mengubah template material default.
    """
    user_divs = await controller.get_user_divisions(current_user.user_id)
    creator_div = user_divs if current_user.role == "PROJECT_MANAGER" else None
    return await controller.handle_update_material(current_user.organization_id, material_id, data, creator_div)


@router.delete("/work-types/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_type_material(
    material_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: WorkTypeController = Depends(),
) -> Response:
    """
    Menghapus template material default dari jenis pekerjaan.
    """
    user_divs = await controller.get_user_divisions(current_user.user_id)
    creator_div = user_divs if current_user.role == "PROJECT_MANAGER" else None
    await controller.handle_delete_material(current_user.organization_id, material_id, creator_div)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
