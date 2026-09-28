"""
app/services/plan_transition_service.py
Transisi SK — padanan PUBLISH / ACCEPT / START / REQUEST·APPROVE·RETURN_COMPLETE di prototype/js/domain.js, termasuk checkMembers
dan checkSchedule. Pesan galat mengikuti prototipe.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from app.core.enums import PlanStatus
from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.signing import canonical
from app.core.time import jakarta_now
from app.repositories.plan_member_repo import PlanMemberRepo
from app.repositories.plan_transition_repo import PlanTransitionRepo
from app.repositories.weekly_report_repo import WeeklyReportRepo
from app.services.signature_service import ACCEPTOR, APPROVER, ISSUER, SignatureService

# domain.js CANCEL_PLAN requireStatus
CANCELLABLE = {PlanStatus.PUBLISHED, PlanStatus.ACCEPTED, PlanStatus.APPEALED, PlanStatus.IN_PROGRESS,
               PlanStatus.COMPLETION_REVIEW}


def _invalid(message: str) -> AppError:
    return AppError("VALIDATION_ERROR", message, status=422)


def _state(message: str) -> AppError:
    return AppError("INVALID_STATE", message, status=409)


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
        # Fase 6 (keputusan pemilik 2026-09-26): penerbit menandatangani dokumen saat terbit.
        await SignatureService(self.repo.db).sign_latest_plan_document(plan_id, issuer, ISSUER, user_id)
        return await self.repo.get_plan(plan_id)

    async def accept(self, plan_id: UUID, org_id: str, user_id: str, row_version: int) -> Any:
        plan = await self._load(plan_id, org_id, row_version, PlanStatus.PUBLISHED)
        await self._leader_only(plan_id, user_id)
        await self._check_members(plan)
        leader = await self.repo.employee_id_of(user_id)
        await self.repo.set_status(plan_id, PlanStatus.ACCEPTED)
        await self.repo.accept_document(plan_id, leader or "")
        if leader:   # ketua menurut SK menandatangani sebagai penerima (fase 6)
            await SignatureService(self.repo.db).sign_latest_plan_document(plan_id, leader, ACCEPTOR, user_id)
        return await self.repo.get_plan(plan_id)

    async def appeal(self, plan_id: UUID, org_id: str, user_id: str, row_version: int, reason: str) -> Any:
        """domain.js APPEAL — ketua menurut SK, hanya dari PUBLISHED, alasan wajib."""
        await self._load(plan_id, org_id, row_version, PlanStatus.PUBLISHED)
        await self._leader_only(plan_id, user_id)
        if not reason.strip():
            raise AppError("VALIDATION_ERROR", "Alasan banding wajib diisi.", status=422)
        await self.repo.appeal(plan_id, reason.strip())
        return await self.repo.get_plan(plan_id)

    async def revise(self, plan_id: UUID, org_id: str, row_version: int) -> Any:
        """domain.js REVISE — PM unit/OPS (dijaga router), hanya dari APPEALED."""
        await self._load(plan_id, org_id, row_version, PlanStatus.APPEALED)
        await self.repo.revise(plan_id)
        return await self.repo.get_plan(plan_id)

    async def cancel_plan(self, plan_id: UUID, org_id: str, row_version: int, reason: str) -> Any:
        """domain.js CANCEL_PLAN — PM unit/OPS (dijaga router); draf diarsipkan, bukan dibatalkan."""
        plan = await self.repo.lock_plan(plan_id, org_id)
        if plan is None:
            raise NotFoundError("SK")
        if plan.status not in CANCELLABLE:
            raise AppError("INVALID_STATE", "Tahap work plan belum sesuai untuk tindakan ini.", status=409)
        if plan.row_version != row_version:
            raise ConflictError()
        if not reason.strip():
            raise _invalid("Alasan pembatalan wajib diisi.")
        await self.repo.cancel(plan_id, reason.strip())
        return await self.repo.get_plan(plan_id)

    async def delete_plan(self, plan_id: UUID, org_id: str, user_id: str, row_version: int, reason: str) -> Any:
        """domain.js DELETE_PLAN — arsip (soft delete) draf yang belum pernah punya SK."""
        await self._load(plan_id, org_id, row_version, PlanStatus.DRAFT)
        if not reason.strip():
            raise _invalid("Alasan pengarsipan wajib diisi.")
        if await self.repo.has_active_allocation(plan_id):
            raise AppError("INVALID_STATE", "Lepaskan reservasi aset sebelum mengarsipkan draft.", status=409)
        if await self.repo.ever_published(plan_id):
            raise AppError("INVALID_STATE",
                           "Pekerjaan yang pernah memiliki SK tidak dapat diarsipkan. Gunakan opsi pembatalan.",
                           status=409)
        await self.repo.archive(plan_id, user_id, reason.strip())
        return await self.repo.get_plan(plan_id)

    async def restore_plan(self, plan_id: UUID, org_id: str, row_version: int) -> Any:
        """domain.js RESTORE_PLAN — hanya draf terarsip; tim diperiksa ulang (checkMembers)."""
        plan = await self.repo.lock_plan(plan_id, org_id, include_archived=True)
        if plan is None:
            raise NotFoundError("SK")
        if not plan.archived:
            raise AppError("INVALID_STATE", "Draft tidak berada di arsip.", status=409)
        if plan.row_version != row_version:
            raise ConflictError()
        await self._check_members(plan)
        await self.repo.restore(plan_id)
        return await self.repo.get_plan(plan_id)

    async def start(self, plan_id: UUID, org_id: str, user_id: str, row_version: int) -> Any:
        plan = await self._load(plan_id, org_id, row_version, PlanStatus.ACCEPTED)
        await self._leader_only(plan_id, user_id)
        today = jakarta_now().date()  # jam server, bukan perangkat (aturan inti #3)
        if plan.period_start > today:
            raise _invalid(f"Pekerjaan baru dapat dimulai pada {plan.period_start:%d-%m-%Y}.")
        await self._check_members(plan)
        if await self.repo.has_unchecked_vehicle(plan_id):
            raise _state("Semua kendaraan harus diperiksa dan dinyatakan layak oleh pengemudi sebelum pekerjaan dimulai.")
        await self.repo.set_status(plan_id, PlanStatus.IN_PROGRESS)
        await self.repo.activate_reserved_assets(plan_id)
        return await self.repo.get_plan(plan_id)

    # ── Penyelesaian (V-26) ───────────────────────────────────────────────────────────────────
    async def final_report(self, plan_id: UUID) -> Any:
        """Laporan akhir untuk dibaca tim & pemeriksa (akses VIEW diperiksa penjaga rute). None bila belum ada."""
        return await self.repo.final_report(plan_id)

    async def _weeks_approved(self, plan_id: UUID) -> bool:
        weeks = await WeeklyReportRepo(self.repo.db).list_weeks(plan_id)
        return all(week.status == "APPROVED" for week in weeks)

    async def request_complete(self, plan_id: UUID, org_id: str, user_id: str, row_version: int,
                               body: str, obstacle: str, file_ids: list[UUID]) -> Any:
        """domain.js REQUEST_COMPLETE — ketua menurut SK (dijaga router)."""
        await self._load(plan_id, org_id, row_version, PlanStatus.IN_PROGRESS)
        if await self.repo.has_open_change(plan_id):
            raise _state("Masih ada usulan perubahan yang belum selesai.")
        if not await self.repo.all_days_approved(plan_id):
            raise _state("Seluruh laporan harian wajib disetujui PM terlebih dahulu.")
        if not await self._weeks_approved(plan_id):
            raise _state("Laporan mingguan belum selesai.")
        if not body.strip() or not obstacle.strip():
            raise _invalid("Laporan penyelesaian dan ringkasan kendala keseluruhan wajib diisi.")
        await self.repo.submit_final_report(plan_id, user_id, body.strip(), obstacle.strip(), file_ids)
        await self.repo.set_status(plan_id, PlanStatus.COMPLETION_REVIEW)
        return await self.repo.get_plan(plan_id)

    async def approve_complete(self, plan_id: UUID, org_id: str, user_id: str, row_version: int,
                               note: str) -> Any:
        """domain.js APPROVE_COMPLETE — PM unit/OPS (dijaga router)."""
        await self._load(plan_id, org_id, row_version, PlanStatus.COMPLETION_REVIEW)
        if not await self.repo.all_days_approved(plan_id):
            raise _state("Terdapat laporan harian yang belum disetujui.")
        if not await self._weeks_approved(plan_id):
            raise _state("Terdapat laporan mingguan yang belum disetujui.")
        if await self.repo.final_report_status(plan_id) != "SUBMITTED":
            raise _state("Laporan akhir belum diserahkan.")
        if await self.repo.has_active_allocation(plan_id):
            raise _state("Masih ada aset yang belum dikembalikan atau diverifikasi (Asset).")
        # R-19 (P6-4): laporan akhir dibekukan & ditandatangani — ketua (penerbit) dan pemeriksa (APPROVER).
        approver = await self.repo.employee_id_of(user_id)
        snapshot = await self.repo.final_report_snapshot(plan_id, approver, note.strip() or None)
        frozen = json.loads(snapshot) if isinstance(snapshot, str) else snapshot
        await self.repo.store_final_snapshot(plan_id, json.dumps(frozen), hashlib.sha256(canonical(frozen)).digest())
        await self.repo.review_final_report(plan_id, user_id, "APPROVED", note.strip() or None)
        await self.repo.set_status(plan_id, PlanStatus.COMPLETED)
        signatures = SignatureService(self.repo.db)
        leader = await self.repo.final_report_submitter(plan_id)
        if leader:
            await signatures.sign_final_report(plan_id, leader, ISSUER, user_id)
        if approver:
            await signatures.sign_final_report(plan_id, approver, APPROVER, user_id)
        return await self.repo.get_plan(plan_id)

    async def return_complete(self, plan_id: UUID, org_id: str, user_id: str, row_version: int,
                              reason: str) -> Any:
        """domain.js RETURN_COMPLETE — PM unit/OPS (dijaga router), alasan wajib."""
        await self._load(plan_id, org_id, row_version, PlanStatus.COMPLETION_REVIEW)
        if not reason.strip():
            raise _invalid("Alasan pengembalian wajib diisi.")
        await self.repo.review_final_report(plan_id, user_id, "CHANGES_REQUESTED", reason.strip())
        await self.repo.set_status(plan_id, PlanStatus.IN_PROGRESS)
        return await self.repo.get_plan(plan_id)
