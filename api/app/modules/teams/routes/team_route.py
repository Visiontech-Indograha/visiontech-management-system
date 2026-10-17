"""
app/modules/teams/routes/team_route.py
Rute API HTTP untuk entitas tim dan anggota lapangan.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.teams.controllers.team_controller import TeamController
from app.modules.teams.schemas.team_schema import (
    MemberAdd,
    TeamCreate,
    TeamDetail,
    TeamListItem,
    TeamUpdate,
)

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=list[TeamListItem])
async def list_teams(
    division_id: UUID | None = Query(None, description="Filter berdasarkan ID divisi"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> list[TeamListItem]:
    """Mengambil daftar seluruh tim operasional."""
    return await controller.handle_list_teams(current_user, division_id)


@router.get("/{team_id}", response_model=TeamDetail)
async def get_team(
    team_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> TeamDetail:
    """Mengambil detail tim operasional beserta anggota aktifnya."""
    return await controller.handle_get_team(current_user, team_id)


@router.post("", response_model=TeamListItem, status_code=201)
async def create_team(
    data: TeamCreate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> TeamListItem:
    """Membuat tim operasional baru."""
    return await controller.handle_create_team(current_user, data)


@router.put("/{team_id}", response_model=TeamListItem)
async def update_team(
    team_id: UUID,
    data: TeamUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> TeamListItem:
    """Memperbarui informasi tim operasional."""
    return await controller.handle_update_team(current_user, team_id, data)


@router.delete("/{team_id}")
async def delete_team(
    team_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> dict[str, str]:
    """Menghapus (soft delete) tim operasional."""
    return await controller.handle_delete_team(current_user, team_id)


@router.post("/{team_id}/members", status_code=201)
async def add_member(
    team_id: UUID,
    data: MemberAdd,
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> dict[str, str]:
    """Menambahkan anggota karyawan ke dalam tim."""
    return await controller.handle_add_member(current_user, team_id, data)


@router.delete("/{team_id}/members/{employee_id}")
async def remove_member(
    team_id: UUID,
    employee_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> dict[str, str]:
    """Mengeluarkan anggota dari tim operasional."""
    return await controller.handle_remove_member(current_user, team_id, employee_id)
