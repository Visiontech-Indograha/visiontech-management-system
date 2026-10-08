"""
app/services/plan_amendment_service.py
Adendum saat SK Berjalan (alur SK v2 PR3, flowchart SK2-E): ketua mengajukan (alasan) → status SK tetap
Berjalan → PM menolak (catatan) atau menerima dengan mengubah isi SK → dokumen adendum ditandatangani PM →
ketua menerima (tanda tangan) → versi SK lama Tidak berlaku.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChangeStatus, ChangeType, DocumentKind, DocumentStatus, PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError, trigger_rule_error
from app.core.time import jakarta_now
from app.crud.crud_asset_reservation import CRUDAssetReservation
from app.crud.crud_plan_amendment import CRUDPlanAmendment
from app.crud.crud_plan_change import CRUDPlanChange
from app.crud.crud_plan_draft import CRUDPlanDraft
from app.crud.crud_plan_transition import CRUDPlanTransition
from app.schemas.plan_draft import PlanDraftRequest
from app.services.access_service import PlanAccess, require_plan_status
from app.services.notification_service import NotificationService
from app.services.plan_draft_service import PlanDraftService
from app.services.signature_service import ACCEPTOR, ISSUER, SignatureService

LOCKED_REPORTS = ("SUBMITTED", "APPROVED")


def _state(message: str) -> AppError:
    return AppError("INVALID_STATE", message, status=409)


class PlanAmendmentService:
    """
    Layanan yang mengelola proses perubahan atau adendum terhadap SK yang sedang berjalan.
    Proses ini mencakup usulan perubahan, persetujuan PM, penerbitan dokumen adendum, dan penerimaan ketua tim.
    """
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDPlanAmendment(db)
        self.changes = CRUDPlanChange(db)
        self.plans = CRUDPlanTransition(db)
        self.drafts = CRUDPlanDraft(db)
        self.assets = CRUDAssetReservation(db)
        self.notify = NotificationService(db)

    async def list_changes(self, plan_id: UUID) -> list[Any]:
        return await self.repo.list_changes(plan_id)

    async def _employee(self, user_id: str) -> str:
        employee = await self.changes.employee_of(user_id)
        if employee is None:
            raise ForbiddenError("Akun Anda belum tertaut ke data karyawan.")
        return str(employee)

    async def _change(self, access: PlanAccess, change_id: UUID, status: ChangeStatus) -> Any:
        change = await self.changes.lock_change(change_id, access.user.organization_id)
        if change is None or str(change.work_plan_id) != str(access.plan.id) or change.change_type != ChangeType.AMENDMENT:
            raise NotFoundError("Permintaan revisi")
        if change.status != status:
            raise _state("Permintaan revisi tidak dalam tahap ini.")
        return change

    async def request_amendment(self, access: PlanAccess, reason: str) -> Any:
        """
        Ketua menurut SK (dijaga router) mengajukan adendum saat Diterima atau Berjalan; status SK tidak berubah.

        Args:
            access: Obyek PlanAccess yang memvalidasi hak pengguna terhadap SK.
            reason: Alasan mengapa adendum ini diperlukan.

        Returns:
            Any: ID dari objek perubahan yang baru dibuat.
        """
        require_plan_status(access, PlanStatus.ACCEPTED, PlanStatus.IN_PROGRESS)
        if not reason.strip():
            raise ValidationError("Alasan revisi wajib diisi.")
        # Validasi: Tidak boleh ada lebih dari satu usulan perubahan yang terbuka sekaligus
        if await self.changes.open_change(access.plan.id) is not None:
            raise _state("Masih ada usulan perubahan yang menunggu penyelesaian.")
        requester = await self._employee(access.user.user_id)
        revision = int(access.plan.revision)
        change_id = await self.changes.insert_change(
            plan_id=access.plan.id, change_type=ChangeType.AMENDMENT, status=ChangeStatus.PENDING_PM,
            reason=reason.strip(), base_revision=revision, proposed_revision=revision + 1, requested_by=requester)
        await self.notify.amendment_requested(access.plan.id, reason.strip())
        return change_id

    async def reject_amendment(self, access: PlanAccess, change_id: UUID, reason: str) -> None:
        """PM menolak usulan; catatan dikirim ke ketua."""
        change = await self._change(access, change_id, ChangeStatus.PENDING_PM)
        if not reason.strip():
            raise ValidationError("Catatan penolakan wajib diisi.")
        await self.changes.set_change(change.id, ChangeStatus.REJECTED, await self._employee(access.user.user_id),
                                      reason.strip())
        await self.notify.amendment_decided(access.plan.id, accepted=False, note=reason.strip())

    async def rewrite_days(self, plan: Any, data: PlanDraftRequest, user: Any) -> None:
        """Menulis ulang header, hari, dan tugas rencana kerja yang sudah terbit (dipakai adendum dan revisi PM).
        Hari yang sudah berlaporan tidak boleh dihapus; isi hari yang laporannya terkirim/disetujui tidak diubah."""
        # Mencegah penghapusan hari yang sudah memiliki data laporan harian
        days = {str(d.work_date): d for d in await self.repo.days_with_report_state(plan.id)}
        wanted = {str(d.work_date): d for d in data.days}
        for work_date, day in days.items():
            if work_date not in wanted and (day.report_status or day.has_member_reports):
                raise ValidationError(f"Hari {work_date} sudah berlaporan dan tidak dapat dihapus.")

        site_id, site_name = await PlanDraftService(self.db)._site(user, str(plan.unit_id), data)
        await self.repo.update_header(
            plan.id, title=data.title.strip(), description=data.description.strip(), category=data.category,
            site_id=site_id, location_text=site_name, period_start=data.period_start, period_end=data.period_end,
            is_out_of_town=data.is_out_of_town)
        for order, new_day in enumerate(sorted(data.days, key=lambda d: d.work_date)):
            key = str(new_day.work_date)
            current = days.get(key)
            if current is not None and current.report_status in LOCKED_REPORTS:
                continue   # isi hari yang laporannya sudah dikirim/disetujui tidak diubah
            if current is None:
                day_id = await self.drafts.insert_day(plan.id, new_day.work_date, new_day.tasks[0].title.strip(), order)
            else:
                day_id = current.id
                await self.repo.clear_tasks(day_id, new_day.tasks[0].title.strip())
            for t_order, task in enumerate(new_day.tasks):
                task_id = await self.drafts.insert_task(day_id, task.title.strip(), task.description.strip(), t_order)
                for f_order, file_id in enumerate(dict.fromkeys(task.file_ids)):
                    await self.drafts.insert_task_file(task_id, file_id, f_order)
        for work_date, day in days.items():
            if work_date not in wanted:
                await self.repo.delete_day(day.id)



    async def apply_amendment(self, access: PlanAccess, change_id: UUID, data: PlanDraftRequest) -> Any:
        """
        PM menerima usulan dengan mengubah isi SK yang sedang berjalan, lalu menandatangani dokumen adendum.

        Args:
            access: Akses pengguna (harus PM unit SK tersebut).
            change_id: ID perubahan yang sedang diproses.
            data: Data draft SK terbaru (hasil amandemen).

        Returns:
            Any: Data detail SK pasca pembaruan.

        Raises:
            ValidationError: Jika ada aturan bisnis yang dilanggar, seperti menghapus hari berlaporan.
        """
        require_plan_status(access, PlanStatus.IN_PROGRESS)
        change = await self._change(access, change_id, ChangeStatus.PENDING_PM)
        plan = access.plan

        # Validasi bisnis: Ketua dan tanggal mulai tidak bisa diubah lewat adendum jenis ini.
        if str(data.leader_employee_id) != str(plan.leader_employee_id):
            raise ValidationError("Ketua tim tidak dapat diganti lewat revisi ini.")
        if data.period_start != plan.period_start:
            raise ValidationError("Tanggal mulai rencana kerja yang sedang berjalan tidak dapat diubah.")
        await PlanDraftService(self.db)._validate(access.user, str(plan.unit_id), data, plan.id)

        await self.rewrite_days(plan, data, access.user)
        today = jakarta_now().date()
        current_members = {m.employee_id for m in await self.repo.open_members(plan.id) if m.role_in_plan == "MEMBER"}
        wanted_members = {str(m) for m in data.member_employee_ids}
        try:
            for removed in current_members - wanted_members:
                await self.repo.close_member(plan.id, removed, today)
            for added in wanted_members - current_members:
                await self.drafts.insert_member(plan.id, added, "MEMBER", max(today, plan.period_start))
            allocated = await self.repo.allocated_asset_ids(plan.id)
            for tool in data.tool_ids:
                if str(tool) not in allocated:
                    await self.assets.insert_allocation(tool, plan.id, None, access.user.user_id)
                    await self.assets.set_asset_status(tool, "IN_USE")
        except IntegrityError as exc:
            raise (trigger_rule_error(exc) or _state("Jadwal bentrok dengan rencana kerja lain.")) from None

        version = await self.changes.next_document_version(plan.id)
        raw = await self.plans.snapshot(plan.id)
        snapshot = json.loads(raw) if isinstance(raw, str) else raw
        issuer = await self._employee(access.user.user_id)
        await self.changes.issue_addendum(change.id, plan.id, DocumentKind.ADDENDUM, version, snapshot, issuer,
                                          change.reason)
        await SignatureService(self.db).sign_latest_plan_document(plan.id, issuer, ISSUER, access.user.user_id)
        await self.changes.set_change(change.id, ChangeStatus.AWAITING_LEADER_ACCEPTANCE, issuer)
        await self.notify.amendment_decided(plan.id, accepted=True, note=None)
        return await PlanDraftService(self.db).detail(plan.id)

    async def accept_amendment(self, access: PlanAccess, change_id: UUID) -> None:
        """Ketua menandatangani adendum; versi SK lama menjadi Tidak berlaku."""
        change = await self._change(access, change_id, ChangeStatus.AWAITING_LEADER_ACCEPTANCE)
        leader = await self._employee(access.user.user_id)
        await self.changes.set_document(change.document_id, DocumentStatus.EFFECTIVE, leader)
        await SignatureService(self.db).sign_latest_plan_document(access.plan.id, leader, ACCEPTOR, access.user.user_id)
        await self.repo.supersede_effective(access.plan.id, change.document_id)
        await self.changes.set_change(change.id, ChangeStatus.EFFECTIVE)
        await self.repo.set_revision(access.plan.id, await self.changes.next_document_version(access.plan.id) - 1)
        await self.notify.amendment_accepted(access.plan.id)

