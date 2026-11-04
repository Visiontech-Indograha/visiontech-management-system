"""
app/modules/teams/routes/team_route.py
Rute API HTTP untuk entitas tim dan anggota lapangan.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import Response as RawResponse

from app.api.deps import get_current_user, require_permission
from app.core.list_params import ListParams, apply_list
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.core.time import utcnow
from app.modules.teams.controllers.team_controller import TeamController
from app.modules.teams.schemas.team_schema import (
    AvailableMemberOut,
    MemberAdd,
    TeamAvailabilityItem,
    TeamCreate,
    TeamDetail,
    TeamListItem,
    TeamLogoOut,
    TeamUpdate,
)
from app.shared.documents.branding import TEAM_LOGO_MAX_BYTES

router = APIRouter(prefix="/teams", tags=["Teams"])
_VIEW = Depends(require_permission(Permission.VIEW_TEAMS))
_MANAGE = Depends(require_permission(Permission.MANAGE_TEAMS))


@router.get("", response_model=list[TeamListItem])
async def list_teams(
    response: Response,
    params: ListParams = Depends(),
    active: bool | None = Query(None, description="Hanya tim aktif (true) atau nonaktif (false)"),
    division_id: UUID | None = Query(None, description="Filter berdasarkan ID divisi"),
    current_user: CurrentUser = _VIEW,
    controller: TeamController = Depends(),
) -> list[TeamListItem]:
    """Mengambil daftar seluruh tim operasional."""
    rows = await controller.handle_list_teams(current_user, division_id)
    return list(
        apply_list(
            rows,
            params,
            response,
            lambda r: (r.name, r.leader_name, r.division_name, r.office_name),
            extra=lambda r: active is None or r.status == active,
        )
    )


@router.get("/availability", response_model=list[TeamAvailabilityItem])
async def get_teams_availability(
    work_date: date | None = Query(None, description="Tanggal kerja (default: hari ini)"),
    division_id: UUID | None = Query(None, description="Filter ID divisi (opsional)"),
    current_user: CurrentUser = _VIEW,
    controller: TeamController = Depends(),
) -> list[TeamAvailabilityItem]:
    """Mengambil status ketersediaan dan beban tugas tim pada tanggal yang dipilih."""
    target_date = work_date or utcnow().date()
    return await controller.handle_get_teams_availability(current_user, target_date, division_id)


@router.get("/available-members", response_model=list[AvailableMemberOut])
async def list_available_members(
    division_id: UUID = Query(..., description="ID divisi yang dicari anggotanya"),
    current_user: CurrentUser = _VIEW,
    controller: TeamController = Depends(),
) -> list[AvailableMemberOut]:
    """Daftar karyawan lapangan aktif di divisi ini yang belum tergabung dalam tim aktif."""
    return await controller.handle_list_available_members(current_user, division_id)


@router.get("/{team_id}", response_model=TeamDetail)
async def get_team(
    team_id: UUID,
    current_user: CurrentUser = _VIEW,
    controller: TeamController = Depends(),
) -> TeamDetail:
    """Mengambil detail tim operasional beserta anggota aktifnya."""
    return await controller.handle_get_team(current_user, team_id)


@router.post("", response_model=TeamListItem, status_code=201)
async def create_team(
    data: TeamCreate,
    current_user: CurrentUser = _MANAGE,
    controller: TeamController = Depends(),
) -> TeamListItem:
    """Membuat tim operasional baru."""
    return await controller.handle_create_team(current_user, data)


@router.put("/{team_id}", response_model=TeamListItem)
async def update_team(
    team_id: UUID,
    data: TeamUpdate,
    current_user: CurrentUser = _MANAGE,
    controller: TeamController = Depends(),
) -> TeamListItem:
    """Memperbarui informasi tim operasional."""
    return await controller.handle_update_team(current_user, team_id, data)


@router.delete("/{team_id}")
async def delete_team(
    team_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: TeamController = Depends(),
) -> dict[str, str]:
    """Menghapus (soft delete) tim operasional."""
    return await controller.handle_delete_team(current_user, team_id)


@router.post("/{team_id}/members", status_code=201)
async def add_member(
    team_id: UUID,
    data: MemberAdd,
    current_user: CurrentUser = _MANAGE,
    controller: TeamController = Depends(),
) -> dict[str, str]:
    """Menambahkan anggota karyawan ke dalam tim."""
    return await controller.handle_add_member(current_user, team_id, data)


@router.delete("/{team_id}/members/{employee_id}")
async def remove_member(
    team_id: UUID,
    employee_id: UUID,
    current_user: CurrentUser = _MANAGE,
    controller: TeamController = Depends(),
) -> dict[str, str]:
    """Mengeluarkan anggota dari tim operasional."""
    return await controller.handle_remove_member(current_user, team_id, employee_id)


@router.put("/{team_id}/logo", response_model=TeamLogoOut)
async def set_team_logo(
    team_id: UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> TeamLogoOut:
    """Mengganti logo tim (PNG/JPEG/WebP, maks 2 MB). Hanya ketua tim tersebut (SUPER_ADMIN darurat)."""
    raw = await file.read(TEAM_LOGO_MAX_BYTES + 1)
    return await controller.handle_set_logo(current_user, team_id, raw)


@router.delete("/{team_id}/logo", status_code=204, response_class=RawResponse)
async def delete_team_logo(
    team_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> RawResponse:
    """Menghapus logo tim → kembali ke logo default. Hanya ketua tim tersebut."""
    await controller.handle_delete_logo(current_user, team_id)
    return RawResponse(status_code=204)


@router.get("/{team_id}/logo", response_class=RawResponse)
async def get_team_logo(
    team_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: TeamController = Depends(),
) -> RawResponse:
    """Isi logo tim (gambar). Anggota tim, PM/OM divisi, HR, dan SUPER_ADMIN; selain itu/tanpa logo → 404."""
    data, mime = await controller.handle_get_logo(current_user, team_id)
    return RawResponse(
        content=data,
        media_type=mime,
        headers={"Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff"},
    )
