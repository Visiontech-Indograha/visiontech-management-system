"""Rute klien (Milestone 10)."""
from __future__ import annotations

from datetime import date  # noqa: F401
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status  # noqa: F401

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.clients.controllers.client_controller import ClientController
from app.modules.clients.schemas.client_schema import (
    ClientCreate,
    ClientOut,
    ClientSiteCreate,
    ClientSiteOut,
    ClientSiteUpdate,
    ClientUpdate,
)

router = APIRouter(prefix="/clients", tags=["Clients"])
_MANAGE = Depends(require_permission(Permission.CREATE_PLAN))


@router.get("", response_model=list[ClientOut])
async def list_clients(
    q: str | None = None,
    active_only: bool = True,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ClientController = Depends(),
) -> list[ClientOut]:
    """Daftar klien: pengelola rencana (create:plan) dan PM/OM/HR. Pekerja lapangan dan ketua tim tidak melihat."""
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

# ── Client Sites (Cabang & Lokasi Klien) ────────────────────────────────────

@router.get("/{client_id}/sites", response_model=list[ClientSiteOut])
async def list_client_sites(
    client_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ClientController = Depends(),
) -> list[ClientSiteOut]:
    """Daftar cabang / lokasi site milik klien."""
    return await controller.list_sites(current_user, client_id)


@router.post("/{client_id}/sites", response_model=ClientSiteOut, status_code=status.HTTP_201_CREATED)
async def create_client_site(
    client_id: UUID,
    data: ClientSiteCreate,
    current_user: CurrentUser = _MANAGE,
    controller: ClientController = Depends(),
) -> ClientSiteOut:
    """Tambah cabang / lokasi site baru untuk klien."""
    return await controller.create_site(current_user, client_id, data)


@router.put("/{client_id}/sites/{site_id}", response_model=ClientSiteOut)
async def update_client_site(
    client_id: UUID,
    site_id: UUID,
    data: ClientSiteUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: ClientController = Depends(),
) -> ClientSiteOut:
    """Ubah data cabang / lokasi site klien."""
    return await controller.update_site(current_user, client_id, site_id, data)


@router.delete("/{client_id}/sites/{site_id}")
async def delete_client_site(
    client_id: UUID,
    site_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: ClientController = Depends(),
) -> dict[str, str]:
    """Hapus cabang / lokasi site klien."""
    return await controller.delete_site(current_user, client_id, site_id)

