"""Rute klien (Milestone 10)."""
from __future__ import annotations

from datetime import date  # noqa: F401
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status  # noqa: F401

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.clients.controllers.client_controller import ClientController
from app.modules.clients.schemas.client_schema import ClientCreate, ClientOut, ClientUpdate

router = APIRouter(prefix="/clients", tags=["Clients"])
_MANAGE = Depends(require_permission(Permission.CREATE_PLAN))


@router.get("", response_model=list[ClientOut])
async def list_clients(
    q: str | None = None,
    active_only: bool = True,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ClientController = Depends(),
) -> list[ClientOut]:
    """Daftar klien."""
    return await controller.list_all(current_user, q, active_only)


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreate,
    current_user: CurrentUser = _MANAGE,
    controller: ClientController = Depends(),
) -> ClientOut:
    """Tambah klien."""
    return await controller.create(current_user, data)


@router.put("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: UUID,
    data: ClientUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: ClientController = Depends(),
) -> ClientOut:
    """Ubah klien (sebagian)."""
    return await controller.update(current_user, client_id, data)


@router.delete("/{client_id}")
async def delete_client(
    client_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: ClientController = Depends(),
) -> dict[str, str]:
    """Hapus (arsip) klien yang belum dipakai."""
    return await controller.delete(current_user, client_id)
