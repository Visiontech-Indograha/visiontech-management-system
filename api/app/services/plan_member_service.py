"""
app/services/plan_member_service.py
Aturan susunan tim SK draft — padanan `checkMembers`/`checkSchedule` di prototype/js/domain.js.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.enums import PlanStatus
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.security import CurrentUser
from app.crud.crud_plan_assignment import CRUDPlanAssignment
from app.crud.crud_plan_member import CRUDPlanMember
from app.services.plan_assignment_service import PlanAssignmentService


@dataclass(frozen=True)
class Team:
    leader_employee_id: str | None
    member_employee_ids: list[str]
    row_version: int


class PlanMemberService:
    """
    Layanan untuk mengelola anggota tim (ketua dan anggota) dari draf SK.
    Mengakomodasi logika penugasan dan validasi personel (checkMembers dan checkSchedule).
    """
    def __init__(self, repo: CRUDPlanMember) -> None:
        """
        Inisialisasi PlanMemberService.

        Args:
            repo (CRUDPlanMember): Repositori untuk operasi anggota tim SK.
        """
        self.repo = repo

    async def team(self, plan_id: UUID) -> list[Any]:
        """
        Mengambil tim aktif untuk detail SK.
        Akses VIEW sudah diperiksa oleh penjaga rute (router).

        Args:
            plan_id (UUID): ID dari SK.

        Returns:
            list[Any]: Daftar anggota tim aktif.
        """
        return await self.repo.active_team(plan_id)

    async def set_team(
        self,
        user: CurrentUser,
        plan_id: UUID,
        leader_id: UUID | None,
        member_ids: list[UUID],
        row_version: int,
    ) -> Team:
        """
        Menetapkan atau memperbarui susunan tim untuk SK yang masih berstatus Draf.
        Memvalidasi agar ketua dan anggota valid, tidak tumpang tindih dengan jadwal lain,
        dan sesuai dengan batasan lingkup PM (Project Manager).

        Args:
            user (CurrentUser): Pengguna yang sedang masuk.
            plan_id (UUID): ID SK.
            leader_id (UUID | None): ID karyawan ketua tim.
            member_ids (list[UUID]): Daftar ID karyawan anggota tim.
            row_version (int): Versi baris untuk kontrol konkurensi (optimistic concurrency control).

        Returns:
            Team: Objek susunan tim yang diperbarui.
        """
        plan = await self.repo.lock_plan(plan_id, user.organization_id)
        if plan is None:
            raise NotFoundError("Rencana Kerja")
        # Validasi: Tim hanya dapat diubah selama SK masih DRAFT
        if plan.status != PlanStatus.DRAFT:
            raise AppError(
                "PLAN_NOT_DRAFT",
                "Susunan tim hanya dapat diubah selama rencana kerja masih draf. Untuk rencana kerja yang sudah terbit, gunakan revisi personel.",
                status=409,
            )
        if plan.row_version != row_version:
            raise ConflictError()

        leader = str(leader_id) if leader_id else None
        members = list(dict.fromkeys(str(m) for m in member_ids))  # buang duplikat, urutan tetap
        # Validasi: Ketua tidak boleh merangkap sebagai anggota
        if leader and leader in members:
            raise AppError("VALIDATION_ERROR", "Ketua tim tidak boleh sekaligus tercatat sebagai anggota.", status=422)
        # Validasi: Ketua tidak boleh PM dari pekerjaan ini
        if leader and plan.pm_employee_id and leader == str(plan.pm_employee_id):
            raise AppError("VALIDATION_ERROR", "Ketua tim tidak boleh sama dengan PM pekerjaan ini.", status=422)

        people = ([leader] if leader else []) + members
        # Validasi ketersediaan karyawan aktif di organisasi
        known = await self.repo.active_employees(people, user.organization_id)
        if set(people) - known:
            raise NotFoundError("Karyawan")
        current = [m.employee_id for m in await self.repo.active_team(plan_id)]

        # Validasi bahwa anggota tim berada dalam unit/otoritas PM yang membuat SK
        await PlanAssignmentService(CRUDPlanAssignment(self.repo.db)).validate_team_scope(
            user, plan.unit_id, people, current_team=current)

        # Memeriksa bentrok jadwal (schedule conflicts) dengan SK/pekerjaan lain
        conflicts = await self.repo.schedule_conflicts(people, plan_id)
        if conflicts:
            numbers = ", ".join(sorted({c.number or c.title for c in conflicts}))
            raise AppError(
                "PERSONNEL_CONFLICT",
                f"Jadwal personel bertabrakan dengan pekerjaan lain: {numbers}.",
                status=409,
                details={"conflicts": [
                    {"employee_id": c.employee_id, "work_plan_id": c.work_plan_id, "number": c.number, "title": c.title}
                    for c in conflicts
                ]},
            )

        # Mengganti anggota dan ketua tim jika validasi lolos
        await self.repo.replace_team(plan_id, plan.period_start, leader, members)
        new_version = await self.repo.set_leader(plan_id, leader)
        return Team(leader_employee_id=leader, member_employee_ids=members, row_version=new_version)
