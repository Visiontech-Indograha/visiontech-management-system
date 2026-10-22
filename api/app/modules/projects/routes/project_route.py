"""Rute proyek (Milestone 10)."""
from __future__ import annotations

from datetime import date  # noqa: F401
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status  # noqa: F401

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.projects.controllers.project_controller import ProjectController
from app.modules.projects.schemas.project_schema import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])
_MANAGE = Depends(require_permission(Permission.CREATE_PLAN))


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    division_id: UUID | None = None,
    client_id: UUID | None = None,
    status: str | None = None,
    q: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ProjectController = Depends(),
) -> list[ProjectOut]:
    """Daftar proyek."""
    return await controller.list_all(current_user, division_id, client_id, status, q)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: CurrentUser = _MANAGE,
    controller: ProjectController = Depends(),
) -> ProjectOut:
    """Tambah proyek."""
    return await controller.create(current_user, data)


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: ProjectController = Depends(),
) -> ProjectOut:
    """Ubah proyek (sebagian)."""
    return await controller.update(current_user, project_id, data)


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: ProjectController = Depends(),
) -> dict[str, str]:
    """Hapus (arsip) proyek yang belum dipakai."""
    return await controller.delete(current_user, project_id)
