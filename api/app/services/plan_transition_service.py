"""
app/services/plan_transition_service.py
Transisi SK — padanan PUBLISH / ACCEPT / START di prototype/js/domain.js, termasuk checkMembers
dan checkSchedule. Pesan galat mengikuti prototipe.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.core.enums import PlanStatus
from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.time import jakarta_now
from app.repositories.plan_member_repo import PlanMemberRepo
from app.repositories.plan_transition_repo import PlanTransitionRepo


def _invalid(message: str) -> AppError:
    return AppError("VALIDATION_ERROR", message, status=422)


class PlanTransitionService:
    def __init__(self, repo: PlanTransitionRepo, members: PlanMemberRepo) -> None:
        self.repo = repo
        self.members = members

    async def _load(self, plan_id: UUID, org_id: str, row_version: int, allowed: PlanStatus) -> Any:
        plan = await self.repo.lock_plan(plan_id, org_id)
        if plan is None:
            raise NotFoundError("SK")
        if plan.status != allowed:
            raise AppError("INVALID_STATE", f"Tindakan ini hanya untuk SK berstatus {allowed.value}.", status=409)
        if plan.row_version != row_version:
            raise ConflictError()
        return plan

    async def _check_members(self, plan: Any) -> None:
        """domain.js checkMembers + checkSchedule."""
        team = await self.repo.active_team(plan.id)
        leaders = [m for m in team if m.role_in_plan == "LEADER"]
        members = [m for m in team if m.role_in_plan == "MEMBER"]
        if len(leaders) != 1 or not leaders[0].employee_active:
            raise _invalid("Ketua tim harus karyawan aktif.")
        if plan.pm_employee_id and leaders[0].employee_id == str(plan.pm_employee_id):
            raise _invalid("PM penerbit tidak boleh menerima SK sebagai ketua tim sendiri.")
        if not members:
            raise _invalid("Pilih minimal satu anggota tim.")
        if any(not m.employee_active for m in members):
            raise _invalid("Semua anggota tim harus karyawan aktif.")
        conflicts = await self.members.schedule_conflicts([m.employee_id for m in team], plan.id)
        if conflicts:
            other = conflicts[0].number or conflicts[0].title or "work plan lain"
            raise AppError("PERSONNEL_CONFLICT", f"Jadwal personel bertabrakan dengan {other}.", status=409)

    async def _leader_only(self, plan_id: UUID, user_id: str) -> None:
        if not await self.repo.is_leader(plan_id, user_id):
            raise ForbiddenError("Hanya ketua tim menurut SK yang berlaku yang dapat melakukan ini.")

    async def publish(self, plan_id: UUID, org_id: str, user_id: str, row_version: int) -> Any:
        plan = await self._load(plan_id, org_id, row_version, PlanStatus.DRAFT)
        await self._check_members(plan)
        if not await self.repo.day_details_complete(plan_id):
            raise _invalid("Rincian harian belum lengkap.")
        issuer = await self.repo.employee_id_of(user_id)
        if issuer is None:
            raise ForbiddenError("Akun Anda belum tertaut ke data karyawan, jadi tidak dapat menerbitkan SK.")

        await self.repo.publish(plan_id)
        snapshot = await self.repo.snapshot(plan_id)
        await self.repo.insert_document(
            plan_id, plan.revision, snapshot if isinstance(snapshot, str) else json.dumps(snapshot), issuer)
        return await self.repo.get_plan(plan_id)

    async def accept(self, plan_id: UUID, org_id: str, user_id: str, row_version: int) -> Any:
        plan = await self._load(plan_id, org_id, row_version, PlanStatus.PUBLISHED)
        await self._leader_only(plan_id, user_id)
        await self._check_members(plan)
        leader = await self.repo.employee_id_of(user_id)
        await self.repo.set_status(plan_id, PlanStatus.ACCEPTED)
        await self.repo.accept_document(plan_id, leader or "")
        return await self.repo.get_plan(plan_id)

    async def start(self, plan_id: UUID, org_id: str, user_id: str, row_version: int) -> Any:
        plan = await self._load(plan_id, org_id, row_version, PlanStatus.ACCEPTED)
        await self._leader_only(plan_id, user_id)
        today = jakarta_now().date()  # jam server, bukan perangkat (aturan inti #3)
        if plan.period_start > today:
            raise _invalid(f"Pekerjaan baru dapat dimulai pada {plan.period_start:%d-%m-%Y}.")
        await self._check_members(plan)
        await self.repo.set_status(plan_id, PlanStatus.IN_PROGRESS)
        return await self.repo.get_plan(plan_id)
