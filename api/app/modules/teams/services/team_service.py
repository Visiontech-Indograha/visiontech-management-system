"""
app/modules/teams/services/team_service.py
Tim lapangan & anggotanya (Milestone 3, docs/36; struktur docs/35 §2: OM → divisi → PM → tim → anggota).

- Lihat tim: izin `view:teams`. PM hanya melihat tim di divisi yang ia pegang (`division.pm_id`).
- Kelola tim: izin `manage:teams` — SUPER_ADMIN semua divisi, PM hanya divisinya sendiri.
- Ketua (`leader_employee_id`) wajib karyawan aktif ber-peran TEAM_LEADER dan selalu tercatat sebagai anggota.
- Anggota hanya akun lapangan (TEAM_LEADER/EMPLOYEE); ketua tidak bisa dikeluarkan dari timnya.
- Tim yang masih dirujuk jadwal harian tidak dapat dihapus (nonaktifkan lewat `status`).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.modules.teams.repositories.team_repository import TeamRepository
from app.modules.teams.schemas.team_schema import TeamCreate, TeamUpdate

FIELD_ROLES = frozenset({"TEAM_LEADER", "EMPLOYEE"})


class TeamService:
    """Use case tim dan anggota."""

    def __init__(self, repo: TeamRepository) -> None:
        self.repo = repo

    @staticmethod
    def _pm_scope(user: CurrentUser) -> str | None:
        """employee_id PM bila pengguna dibatasi ke divisinya sendiri; None = tanpa batas."""
        return user.employee_id if user.has_role("PROJECT_MANAGER") else None

    async def list_teams(self, user: CurrentUser, division_id: UUID | None) -> list[Any]:
        return await self.repo.list_teams(division_id, self._pm_scope(user))

    async def _team(self, user: CurrentUser, team_id: UUID) -> Any:
        team = await self.repo.get(team_id)
        scope = self._pm_scope(user)
        if team is None or (scope is not None and str(team.pm_id) != scope):
            raise NotFoundError("Tim")
        return team

    async def get_team(self, user: CurrentUser, team_id: UUID) -> dict[str, Any]:
        team = await self._team(user, team_id)
        data = dict(team._mapping)
        data["members"] = [dict(m._mapping) for m in await self.repo.members(team_id)]
        return data

    async def _check_division(self, user: CurrentUser, division_id: UUID) -> None:
        division = await self.repo.division(division_id)
        if division is None:
            raise ValidationError("Divisi tidak ditemukan atau sudah nonaktif.")
        scope = self._pm_scope(user)
        if scope is not None and str(division.pm_id) != scope:
            raise AppError("FORBIDDEN", "Anda hanya dapat mengelola tim di divisi yang Anda pegang.", status=403)

    async def _check_leader(self, leader_id: UUID) -> None:
        if await self.repo.employee_role(leader_id) != "TEAM_LEADER":
            raise ValidationError("Ketua tim harus karyawan aktif dengan peran Team Leader.")

    async def _check_name(self, division_id: UUID, name: str, exclude: UUID | None = None) -> None:
        if await self.repo.name_taken(division_id, name, exclude):
            raise AppError("TEAM_NAME_TAKEN", "Nama tim sudah dipakai di divisi ini.", status=409)

    async def create_team(self, user: CurrentUser, data: TeamCreate) -> Any:
        name = data.name.strip()
        await self._check_division(user, data.division_id)
        if not await self.repo.office_active(data.office_id):
            raise ValidationError("Kantor tidak ditemukan atau sudah dihapus.")
        await self._check_leader(data.leader_employee_id)
        await self._check_name(data.division_id, name)
        team_id = await self.repo.insert(data.office_id, data.division_id, data.leader_employee_id, name, data.status)
        await self.repo.add_member(team_id, data.leader_employee_id)
        return await self.repo.get(team_id)

    async def update_team(self, user: CurrentUser, team_id: UUID, data: TeamUpdate) -> Any:
        team = await self._team(user, team_id)
        division_id = data.division_id or team.division_id
        if data.division_id and data.division_id != team.division_id:
            await self._check_division(user, data.division_id)
        if data.office_id and data.office_id != team.office_id and not await self.repo.office_active(data.office_id):
            raise ValidationError("Kantor tidak ditemukan atau sudah dihapus.")
        if data.leader_employee_id and data.leader_employee_id != team.leader_employee_id:
            await self._check_leader(data.leader_employee_id)
        name = data.name.strip() if data.name else None
        if name or data.division_id:
            await self._check_name(division_id, name or team.name, exclude=team_id)
        await self.repo.update(
            team_id, office_id=data.office_id, division_id=data.division_id, leader_id=data.leader_employee_id,
            name=name, status=data.status,
        )
        if data.leader_employee_id:
            await self.repo.add_member(team_id, data.leader_employee_id)
        return await self.repo.get(team_id)

    async def delete_team(self, user: CurrentUser, team_id: UUID) -> None:
        await self._team(user, team_id)
        plans = await self.repo.plan_count(team_id)
        if plans:
            raise AppError(
                "TEAM_IN_USE",
                f"Tim masih dipakai {plans} jadwal harian. Nonaktifkan tim bila tidak lagi bertugas.",
                status=409,
            )
        await self.repo.archive(team_id)

    async def add_member(self, user: CurrentUser, team_id: UUID, employee_id: UUID) -> None:
        await self._team(user, team_id)
        if await self.repo.employee_role(employee_id) not in FIELD_ROLES:
            raise ValidationError("Anggota tim harus karyawan lapangan aktif (Team Leader atau Employee).")
        if await self.repo.is_member(team_id, employee_id):
            raise AppError("MEMBER_EXISTS", "Karyawan ini sudah menjadi anggota tim.", status=409)
        await self.repo.add_member(team_id, employee_id)

    async def remove_member(self, user: CurrentUser, team_id: UUID, employee_id: UUID) -> None:
        team = await self._team(user, team_id)
        if str(team.leader_employee_id) == str(employee_id):
            raise AppError(
                "LEADER_REQUIRED", "Ketua tim tidak dapat dikeluarkan. Ganti ketua tim terlebih dahulu.", status=409
            )
        if not await self.repo.remove_member(team_id, employee_id):
            raise NotFoundError("Anggota tim")
