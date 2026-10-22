"""Rute jabatan (Milestone 10)."""
from __future__ import annotations

from datetime import date  # noqa: F401
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status  # noqa: F401

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.job_positions.controllers.job_position_controller import JobPositionController
from app.modules.job_positions.schemas.job_position_schema import JobPositionCreate, JobPositionOut, JobPositionUpdate

router = APIRouter(prefix="/job-positions", tags=["Job Positions"])
_MANAGE = Depends(require_permission(Permission.MANAGE_USERS))


@router.get("", response_model=list[JobPositionOut])
async def list_job_positions(
    division_id: UUID | None = None,
    active_only: bool = True,
    current_user: CurrentUser = Depends(get_current_user),
    controller: JobPositionController = Depends(),
) -> list[JobPositionOut]:
    """Daftar jabatan."""
    return await controller.list_all(current_user, division_id, active_only)


@router.post("", response_model=JobPositionOut, status_code=status.HTTP_201_CREATED)
async def create_job_position(
    data: JobPositionCreate,
    current_user: CurrentUser = _MANAGE,
    controller: JobPositionController = Depends(),
) -> JobPositionOut:
    """Tambah jabatan."""
    return await controller.create(current_user, data)


@router.put("/{position_id}", response_model=JobPositionOut)
async def update_job_position(
    position_id: UUID,
    data: JobPositionUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: JobPositionController = Depends(),
) -> JobPositionOut:
    """Ubah jabatan (sebagian)."""
    return await controller.update(current_user, position_id, data)


@router.delete("/{position_id}")
async def delete_job_position(
    position_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: JobPositionController = Depends(),
) -> dict[str, str]:
    """Hapus (arsip) jabatan yang belum dipakai."""
    return await controller.delete(current_user, position_id)
