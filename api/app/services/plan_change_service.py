"""
app/services/plan_change_service.py
Adendum SK (V-22) — padanan `domain.js` REQUEST_CHANGE, REQUEST_PERSONNEL_CHANGE, APPROVE_CHANGE,
ACCEPT_CHANGE, REJECT_CHANGE, WITHDRAW_CHANGE. Rencana lama tetap berlaku sampai adendum diterima.
Kewenangan: PM unit/OPS & ketua menurut SK dibaca lewat penjaga V-07; ketua baru pada adendum
personel dikenali dari usulan itu sendiri (ia belum tentu anggota SK).
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChangeStatus, ChangeType, DocumentKind, DocumentStatus, PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.security import CurrentUser
from app.crud.crud_plan_assignment import CRUDPlanAssignment
from app.crud.crud_plan_change import CRUDPlanChange
from app.crud.crud_plan_member import CRUDPlanMember
from app.crud.crud_plan_transition import CRUDPlanTransition
from app.services.access_service import PlanNeed, check_plan_access
from app.services.plan_assignment_service import PlanAssignmentService

ACTIVE = (PlanStatus.ACCEPTED, PlanStatus.IN_PROGRESS)   # domain.js requireStatus(['ACCEPTED','IN_PROGRESS'])
OPEN = (ChangeStatus.PENDING_PM, ChangeStatus.AWAITING_LEADER_ACCEPTANCE)


def _invalid(message: str) -> AppError:
    """Mengembalikan error ketika validasi bisnis untuk usulan perubahan gagal."""
    return AppError("VALIDATION_ERROR", message, status=422)


def _state(message: str = "Status SK belum sesuai untuk tindakan ini. Muat ulang halaman.") -> AppError:
    """Mengembalikan error ketika state/status SK tidak mengizinkan aksi perubahan."""
    return AppError("INVALID_STATE", message, status=409)


def _require_reason(reason: str | None, message: str) -> str:
    """Memastikan argumen 'reason' ada dan tidak kosong, mengembalikan versi string-nya yang sudah di-strip."""
    if not (reason or "").strip():
        raise _invalid(message)
    return (reason or "").strip()


class PlanChangeService:
    """
    Layanan utama yang mengelola usulan perubahan pada SK yang sedang berjalan (adendum),
    termasuk perubahan jadwal/perpanjangan maupun pergantian komposisi tim (personel).
    """
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDPlanChange(db)
        self.plans = CRUDPlanTransition(db)
        self.members = CRUDPlanMember(db)

    async def _snapshot(self, plan_id: UUID | str) -> Any:
        """
        Mengambil snapshot data komprehensif dari suatu rencana kerja untuk disimpan pada addendum.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            Any: Data dict/list snapshot SK.
        """
        raw = await self.plans.snapshot(plan_id)
        return json.loads(raw) if isinstance(raw, str) else raw

    async def _open_plan(self, plan_id: UUID, user: CurrentUser, need: PlanNeed) -> Any:
        """
        Memastikan pengguna berhak mengakses, SK dalam kondisi aktif, dan tidak ada perubahan lain yang sedang menunggu.

        Args:
            plan_id (UUID): ID SK.
            user (CurrentUser): Objek user peminta.
            need (PlanNeed): Kewenangan minimum (PM/Leader/dkk).

        Returns:
            Any: Objek akses dan objek rencana kerja (plan).
        """
        access = await check_plan_access(self.db, plan_id, user, need)
        plan = await self.plans.lock_plan(plan_id, user.organization_id)
        if plan is None:
            raise NotFoundError("SK")
        if plan.status not in ACTIVE:
            raise _state()
        if await self.repo.open_change(plan_id):
            raise AppError("INVALID_STATE", "Masih ada perubahan yang menunggu penyelesaian.", status=409)
        return access, plan

    async def read(self, change_id: UUID | str) -> Any:
        """
        Mengambil detail satu usulan perubahan.

        Args:
            change_id (UUID | str): ID perubahan.

        Returns:
            Any: Objek usulan perubahan.
        """
        return await self.repo.get_change(change_id)

    # ── Pengajuan ────────────────────────────────────────────────────────────────────────────
    async def request_change(self, plan_id: UUID, user: CurrentUser, new_end: date | None, reason: str) -> Any:
        """
        Ketua tim mengajukan usulan perpanjangan SK ke PM (domain.js REQUEST_CHANGE).
        Memerlukan status SK yang aktif (IN_PROGRESS atau ACCEPTED).
        """
        _, plan = await self._open_plan(plan_id, user, PlanNeed.LEADER)
        if new_end is None or new_end <= plan.period_end:
            raise _invalid("Tanggal akhir baru harus setelah akhir rencana saat ini.")
        reason = _require_reason(reason, "Alasan perubahan wajib diisi.")
        version = await self.repo.next_document_version(plan_id)
        return await self.repo.insert_change(
            plan_id=plan_id, change_type=ChangeType.EXTEND, status=ChangeStatus.PENDING_PM, reason=reason,
            base_revision=plan.revision, proposed_revision=version,
            requested_by=await self.repo.employee_of(user.user_id), old_end=plan.period_end, new_end=new_end)

    async def request_personnel_change(self, plan_id: UUID, user: CurrentUser, leader_id: UUID | None,
                                       member_ids: list[UUID], reason: str) -> Any:
        """
        PM mengajukan susunan personel baru (domain.js REQUEST_PERSONNEL_CHANGE).
        Adendum langsung terbit dan menunggu penerimaan oleh ketua tim yang ditunjuk.
        """
        _, plan = await self._open_plan(plan_id, user, PlanNeed.PM_UNIT)
        reason = _require_reason(reason, "Alasan perubahan personel wajib diisi.")
        leader = str(leader_id) if leader_id else (str(plan.leader_employee_id) if plan.leader_employee_id else None)
        members = list(dict.fromkeys(str(m) for m in member_ids))
        if not leader:
            raise _invalid("Ketua tim harus karyawan aktif.")
        if leader in members:
            raise _invalid("Ketua tim tidak perlu didaftarkan lagi sebagai anggota.")
        if plan.pm_employee_id and leader == str(plan.pm_employee_id):
            raise _invalid("PM penerbit tidak boleh menerima SK sebagai ketua tim sendiri.")
        if not members:
            raise _invalid("Pilih minimal satu anggota tim.")
        current = {m.employee_id for m in await self.plans.active_team(plan_id)}
        if {leader, *members} == current and leader == str(plan.leader_employee_id):
            raise _invalid("Tidak ada perubahan personel yang diusulkan.")
        people = [leader, *members]
        if set(people) - await self.members.active_employees(people, user.organization_id):
            raise _invalid("Semua anggota tim harus aktif.")
        await PlanAssignmentService(CRUDPlanAssignment(self.db)).validate_team_scope(
            user, plan.unit_id, people, current_team=current,
        )
        conflicts = await self.members.schedule_conflicts(people, plan_id)
        if conflicts:
            other = conflicts[0].number or conflicts[0].title or "work plan lain"
            raise AppError("PERSONNEL_CONFLICT", f"Jadwal personel bertabrakan dengan {other}.", status=409)
        version = await self.repo.next_document_version(plan_id)
        requester = await self.repo.employee_of(user.user_id)
        change_id = await self.repo.insert_change(
            plan_id=plan_id, change_type=ChangeType.PERSONNEL, status=ChangeStatus.AWAITING_LEADER_ACCEPTANCE,
            reason=reason, base_revision=plan.revision, proposed_revision=version, requested_by=requester,
            leader_id=leader, member_ids=members)
        snapshot = {"sk": await self._snapshot(plan_id), "usulan": {"ketua": leader, "anggota": members}}
        await self.repo.issue_addendum(change_id, plan_id, DocumentKind.PERSONNEL_ADDENDUM, version,
                                       snapshot, requester, reason)
        return change_id

    # ── Keputusan ────────────────────────────────────────────────────────────────────────────
    async def _load(self, change_id: UUID, user: CurrentUser) -> Any:
        """
        Mengunci dan memuat data usulan perubahan dari database.

        Args:
            change_id (UUID): ID usulan perubahan.
            user (CurrentUser): Objek pengguna.

        Returns:
            Any: Baris data usulan perubahan.
        """
        change = await self.repo.lock_change(change_id, user.organization_id)
        if change is None:
            raise NotFoundError("Usulan perubahan")
        return change

    async def _is_incoming_leader(self, change: Any, user: CurrentUser) -> bool:
        """
        Memeriksa apakah pengguna saat ini adalah ketua tim yang diusulkan pada adendum personel ini.

        Args:
            change (Any): Data perubahan.
            user (CurrentUser): Objek pengguna saat ini.

        Returns:
            bool: True jika pengguna adalah ketua tim yang diusulkan.
        """
        return bool(change.proposed_leader_id) and change.proposed_leader_id == await self.repo.employee_of(user.user_id)

    async def approve_change(self, change_id: UUID, user: CurrentUser) -> Any:
        """
        PM menyetujui usulan perpanjangan SK (domain.js APPROVE_CHANGE) dengan menandatanganinya.
        Status perubahan menjadi AWAITING_LEADER_ACCEPTANCE.
        """
        change = await self._load(change_id, user)
        await check_plan_access(self.db, change.work_plan_id, user, PlanNeed.PM_UNIT)
        if change.plan_status not in ACTIVE:
            raise _state()
        if change.status != ChangeStatus.PENDING_PM:
            raise _state("Tidak ada perubahan menunggu persetujuan PM.")
        if change.base_revision != change.plan_revision:
            raise _state("SK sudah berubah sejak usulan ini dibuat. Muat ulang, lalu ajukan perubahan baru.")
        team = [m.employee_id for m in await self.plans.active_team(change.work_plan_id)]
        conflicts = await self.members.schedule_conflicts_until(team, change.work_plan_id, change.new_period_end)
        if conflicts:
            other = conflicts[0].number or conflicts[0].title or "work plan lain"
            raise AppError("PERSONNEL_CONFLICT", f"Jadwal personel bertabrakan dengan {other}.", status=409)
        await self.repo.set_change(change_id, ChangeStatus.AWAITING_LEADER_ACCEPTANCE,
                                   decided_by=await self.repo.employee_of(user.user_id))
        snapshot = {"sk": await self._snapshot(change.work_plan_id),
                    "usulan": {"akhir_baru": change.new_period_end.isoformat()}}
        await self.repo.issue_addendum(change_id, change.work_plan_id, DocumentKind.ADDENDUM,
                                       change.proposed_revision, snapshot,
                                       await self.repo.employee_of(user.user_id), change.reason)
        return change_id

    async def accept_change(self, change_id: UUID, user: CurrentUser) -> Any:
        """
        Ketua tim (atau ketua baru jika ada perubahan personel) menerima adendum (domain.js ACCEPT_CHANGE).
        Mengaktifkan adendum dan memperbarui dokumen terkait menjadi EFFECTIVE.
        """
        change = await self._load(change_id, user)
        if change.change_type == ChangeType.PERSONNEL:
            if not await self._is_incoming_leader(change, user):
                raise ForbiddenError("Hanya ketua tim yang ditunjuk pada adendum personel ini yang dapat menerimanya.")
        else:
            await check_plan_access(self.db, change.work_plan_id, user, PlanNeed.LEADER)
        if change.plan_status not in ACTIVE:
            raise _state()
        if change.status != ChangeStatus.AWAITING_LEADER_ACCEPTANCE:
            raise _state("Adendum belum siap diterima.")
        if change.base_revision != change.plan_revision:
            raise _state("SK sudah berubah sejak usulan ini dibuat. Muat ulang halaman.")
        acceptor = await self.repo.employee_of(user.user_id)
        if change.change_type == ChangeType.PERSONNEL:
            await self.repo.apply_personnel(change.work_plan_id, change.proposed_leader_id,
                                            [str(m) for m in change.proposed_members], change.proposed_revision)
        else:
            await self.repo.apply_extension(change.work_plan_id, change.period_end, change.new_period_end,
                                            change.proposed_revision)
        await self.repo.set_change(change_id, ChangeStatus.EFFECTIVE)
        await self.repo.set_document(change.document_id, DocumentStatus.EFFECTIVE, accepted_by=acceptor)
        return change_id

    async def reject_change(self, change_id: UUID, user: CurrentUser, reason: str | None) -> Any:
        """
        Menolak usulan perubahan SK (domain.js REJECT_CHANGE).
        Perubahan perpanjangan dapat ditolak oleh ketua atau PM;
        perubahan personel hanya dapat ditolak oleh ketua yang ditunjuk.
        """
        change = await self._load(change_id, user)
        if change.change_type == ChangeType.PERSONNEL:
            if not await self._is_incoming_leader(change, user):
                raise ForbiddenError("Hanya ketua tim yang ditunjuk pada adendum personel ini yang dapat menolaknya. "
                                     "PM dapat menarik usulannya sendiri.")
        else:
            access = await check_plan_access(self.db, change.work_plan_id, user, PlanNeed.VIEW)
            if not (access.is_leader or access.manages):
                raise ForbiddenError("Hanya ketua tim atau PM unit pekerjaan ini yang dapat menolak perubahan.")
        if change.plan_status not in ACTIVE:
            raise _state()
        if change.status not in OPEN:
            raise _state("Tidak ada perubahan terbuka.")
        reason = _require_reason(reason, "Alasan wajib diisi.")
        await self.repo.set_change(change_id, ChangeStatus.REJECTED, await self.repo.employee_of(user.user_id), reason)
        await self.repo.set_document(change.document_id, DocumentStatus.REJECTED)
        return change_id

    async def withdraw_change(self, change_id: UUID, user: CurrentUser, reason: str | None) -> Any:
        """
        Menarik kembali usulan perubahan (domain.js WITHDRAW_CHANGE).
        Hanya berlaku untuk PM yang ingin menarik adendum personel yang belum diterima.
        """
        change = await self._load(change_id, user)
        await check_plan_access(self.db, change.work_plan_id, user, PlanNeed.PM_UNIT)
        if change.plan_status not in ACTIVE:
            raise _state()
        if change.status not in OPEN:
            raise _state("Tidak ada usulan perubahan yang terbuka.")
        if change.change_type != ChangeType.PERSONNEL:
            raise _state("Penarikan hanya tersedia untuk adendum personel yang diajukan PM.")
        reason = _require_reason(reason, "Alasan penarikan wajib diisi.")
        await self.repo.set_change(change_id, ChangeStatus.WITHDRAWN, await self.repo.employee_of(user.user_id), reason)
        await self.repo.set_document(change.document_id, DocumentStatus.WITHDRAWN)
        return change_id
