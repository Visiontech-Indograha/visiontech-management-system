"""Rute kelola penugasan peran tambahan (ADR 0002). Hanya SUPER_ADMIN (`manage:role_assignments`)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import IdempotencyGuard, idempotency_guard, require_permission
from app.core.list_params import ListParams, apply_list
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.role_assignments.controllers.role_assignment_controller import RoleAssignmentController
from app.modules.role_assignments.schemas.role_assignment_schema import RoleAssignmentCreate, RoleAssignmentOut

router = APIRouter(prefix="/users/{user_id}/role-assignments", tags=["Role Assignments"])
_MANAGE = Depends(require_permission(Permission.MANAGE_ROLE_ASSIGNMENTS))


@router.get("", response_model=list[RoleAssignmentOut])
async def list_role_assignments(
    user_id: UUID,
    response: Response,
    params: ListParams = Depends(),
    current_user: CurrentUser = _MANAGE,
    controller: RoleAssignmentController = Depends(),
) -> list[RoleAssignmentOut]:
    """Penugasan peran aktif milik satu akun."""
    rows = await controller.handle_list(user_id)
    return list(apply_list(rows, params, response, lambda r: (r.role, r.office_name)))


@router.post("", response_model=RoleAssignmentOut, status_code=status.HTTP_201_CREATED)
async def add_role_assignment(
    user_id: UUID,
    data: RoleAssignmentCreate,
    current_user: CurrentUser = _MANAGE,
    controller: RoleAssignmentController = Depends(),
    idem: IdempotencyGuard = Depends(idempotency_guard),
) -> RoleAssignmentOut | Response:
    """Tambah peran tambahan (maks 2). Mendukung Idempotency-Key (opsional)."""
    tersimpan = idem.tersimpan()
    if tersimpan is not None:
        return tersimpan
    hasil = await controller.handle_add(current_user, user_id, data)
    return await idem.simpan(hasil, status.HTTP_201_CREATED)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_role_assignment(
    user_id: UUID,
    assignment_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: RoleAssignmentController = Depends(),
) -> Response:
    """Cabut penugasan (soft delete). Berlaku seketika pada token yang sama."""
    await controller.handle_revoke(current_user, user_id, assignment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
