"""
Jenis pekerjaan + template foto laporan (Rencana Kerja v3, T9). Tipis (dok 12 §2): aturan di
services/work_type_service.py.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_user, get_work_type_service, plan_access, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.work_type import WorkTypeIn, WorkTypeOut, WorkTypePhotoOut
from app.services.access_service import PlanAccess, PlanNeed
from app.services.work_type_service import WorkTypeService

router = APIRouter(tags=["Work Types"])
_MANAGE = Depends(require_permission(Permission.CREATE_PLAN))
_VIEW = Depends(plan_access(PlanNeed.VIEW))


def _out(row: object) -> WorkTypeOut:
    return WorkTypeOut(**row._mapping)  # type: ignore[attr-defined]


@router.get("/work-types", response_model=list[WorkTypeOut])
async def list_work_types(all: bool = False, current_user: CurrentUser = Depends(get_current_user),
                          service: WorkTypeService = Depends(get_work_type_service)) -> list[WorkTypeOut]:
    """
    Daftar jenis pekerjaan beserta template foto (GET). Semua yang masuk melihat yang aktif;
    `?all=true` (termasuk yang nonaktif) hanya untuk pengelola rencana kerja.

    Query Parameters:
    - all (bool): sertakan yang nonaktif (butuh izin create:plan).

    Returns:
    - list[WorkTypeOut]: jenis pekerjaan.
    """
    include_inactive = all and Permission.CREATE_PLAN in current_user.permissions
    return [_out(r) for r in await service.list_types(current_user.organization_id, include_inactive)]


@router.post("/work-types", response_model=WorkTypeOut, status_code=status.HTTP_201_CREATED)
async def create_work_type(data: WorkTypeIn, current_user: CurrentUser = _MANAGE,
                           service: WorkTypeService = Depends(get_work_type_service)) -> WorkTypeOut:
    """
    Membuat jenis pekerjaan + template foto (POST) — PM/OPS.

    Request Body:
    - data (WorkTypeIn): nama dan daftar slot foto.

    Returns:
    - WorkTypeOut: jenis yang dibuat.
    """
    return _out(await service.create(current_user.organization_id, data))


@router.put("/work-types/{type_id}", response_model=WorkTypeOut)
async def update_work_type(type_id: UUID, data: WorkTypeIn, current_user: CurrentUser = _MANAGE,
                           service: WorkTypeService = Depends(get_work_type_service)) -> WorkTypeOut:
    """
    Mengubah nama dan mengganti seluruh daftar slot foto (PUT) — PM/OPS. Mengaktifkan kembali jenis nonaktif.

    Path Parameters:
    - type_id (UUID): ID jenis pekerjaan.

    Returns:
    - WorkTypeOut: jenis setelah diubah.
    """
    return _out(await service.update(current_user.organization_id, type_id, data))


@router.delete("/work-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_work_type(type_id: UUID, current_user: CurrentUser = _MANAGE,
                               service: WorkTypeService = Depends(get_work_type_service)) -> Response:
    """
    Menonaktifkan jenis pekerjaan (DELETE) — PM/OPS. Tidak dihapus: rencana kerja lama tetap utuh.

    Path Parameters:
    - type_id (UUID): ID jenis pekerjaan.
    """
    await service.deactivate(current_user.organization_id, type_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/work-plans/{plan_id}/photo-template", response_model=list[WorkTypePhotoOut])
async def plan_photo_template(plan_id: UUID, day_id: UUID | None = None, access: PlanAccess = _VIEW,
                              service: WorkTypeService = Depends(get_work_type_service)) -> list[WorkTypePhotoOut]:
    """
    Template foto laporan rencana kerja (GET) — kosong bila rencana kerja tanpa jenis pekerjaan.

    Path Parameters:
    - plan_id (UUID): ID rencana kerja.

    Query Parameters:
    - day_id (UUID, opsional): hari kerja; memakai jenis khusus hari itu bila ada.

    Returns:
    - list[WorkTypePhotoOut]: slot foto berurutan.
    """
    return [WorkTypePhotoOut(**r._mapping) for r in await service.template_of_plan(plan_id, day_id)]
