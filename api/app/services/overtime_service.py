"""
app/services/overtime_service.py
Aturan bisnis lembur (V-28) — domain.js REPORT_OVERTIME (baris 607–614), REVIEW_OVERTIME (616–627).
Router tipis → service → crud; aturan bisnis di sini, SQL di crud.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import Permission, RoleCode
from app.core.security import CurrentUser
from app.crud.crud_org_clock import CRUDOrgClock
from app.crud.crud_overtime import CRUDOvertime
from app.crud.crud_plan_access import CRUDPlanAccess
from app.services.access_service import PlanNeed, check_plan_access


def _state(msg: str) -> AppError:
    """Helper untuk melempar AppError status 409 (Conflict)."""
    return AppError("INVALID_STATE", msg, status=409)


class OvertimeService:
    """Layanan pengelolaan pengajuan dan persetujuan lembur."""
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDOvertime(db)

    # ------------------------------------------------------------------
    # domain.js REPORT_OVERTIME (baris 607–614)
    # ------------------------------------------------------------------
    async def report(self, user: CurrentUser, plan_id: UUID, hours: float, reason: str) -> Any:
        """
        Mengajukan lembur pada suatu SK yang sedang berjalan (IN_PROGRESS).
        Diakses oleh ketua tim atau anggota. Sesuai alur pada domain.js baris 607-614.

        Args:
            user: Informasi pengguna.
            plan_id: ID SK pekerjaan.
            hours: Jumlah jam lembur (maksimal 12 jam).
            reason: Alasan pelaksanaan lembur.

        Returns:
            Any: Data pengajuan lembur yang baru dibuat.
        """
        # SK tidak terlihat / organisasi lain → 404 (V-07/V-08).
        access = await check_plan_access(self.db, plan_id, user, PlanNeed.VIEW)
        if access.plan.status != PlanStatus.IN_PROGRESS:
            raise _state("Hanya pekerjaan aktif yang bisa diajukan lembur.")
        if not 0 < hours <= 12:
            raise ValidationError("Jam lembur harus lebih dari 0 dan paling banyak 12 jam.")
        reason = reason.strip()
        if not reason:
            raise ValidationError("Alasan lembur wajib diisi.")
        # Hanya pihak yang terlibat langsung yang dapat mengajukan lembur
        if not (access.is_leader or access.is_member):
            raise ForbiddenError("Hanya ketua atau anggota pekerjaan ini yang dapat mengajukan lembur.")

        # Tanggal dari server (V-10, domain.js memakai state.demoDate — bukan tanggal klien).
        today = (await CRUDOrgClock(self.db).local_now(user.organization_id)).today

        emp_id = await self.repo.employee_of(user.user_id)
        if emp_id is None:
            raise ValidationError("Akun tidak terhubung ke data karyawan.")

        # domain.js baris 612: dokumen EFFECTIVE terbaru yang berlaku saat diajukan.
        doc_id = await self.repo.effective_document_id(plan_id)

        try:
            row = await self.repo.insert(
                org_id=user.organization_id,
                plan_id=plan_id,
                doc_id=doc_id,
                employee_id=emp_id,
                work_date=today,
                hours=hours,
                reason=reason,
            )
        except IntegrityError:
            # unique index overtime_no_double_uidx: satu pengajuan non-REJECTED per (emp, plan, date).
            raise _state(
                "Pengajuan lembur untuk hari ini di pekerjaan ini sudah ada dan sedang dalam proses."
            ) from None

        return row

    # ------------------------------------------------------------------
    # domain.js REVIEW_OVERTIME (baris 616–627)
    # ------------------------------------------------------------------
    async def review(
        self, user: CurrentUser, overtime_id: UUID, decision: str, note: str | None
    ) -> Any:
        """
        PM unit atau tim OPS memberikan persetujuan atau penolakan atas pengajuan lembur.
        Lembur harus dalam status 'PENDING_PM'. Sesuai alur pada domain.js baris 616-627.

        Args:
            user: Pengguna yang melakukan review.
            overtime_id: ID pengajuan lembur.
            decision: Keputusan (APPROVED atau REJECTED).
            note: Catatan tambahan opsional.

        Returns:
            Any: Data lembur setelah status diubah.
        """
        ot = await self.repo.get_for_review(overtime_id, user.organization_id)
        if ot is None:
            raise NotFoundError("Lembur")

        # domain.js baris 618: hanya yang masih PENDING_PM.
        if ot.status != "PENDING_PM":
            raise _state("Pengajuan lembur ini sudah diperiksa atau tidak dapat diperiksa lagi.")

        # domain.js baris 620: can(actor, 'REVIEW_OVERTIME', unit) = PM unit SK, OPS, ADMIN.
        # Realisasi: cek plan.manages (PM unit / OPS / ADMIN) dari CRUDPlanAccess.
        plan_access = await CRUDPlanAccess(self.db).standing(
            ot.work_plan_id, user.organization_id, user.user_id
        )
        if plan_access is None or not plan_access.manages:
            raise ForbiddenError(
                "Lembur ini berada di luar unit atau kewenangan Anda."
            )

        # domain.js baris 621: pengaju tidak dapat menyetujui sendiri.
        reviewer_emp = await self.repo.employee_of(user.user_id)
        if reviewer_emp is None or str(reviewer_emp) == str(ot.employee_id):
            raise ForbiddenError("Pengaju lembur tidak dapat menyetujui pengajuannya sendiri.")

        # domain.js: keputusan diperiksa terakhir.
        if decision not in ("APPROVED", "REJECTED"):
            raise ValidationError("Keputusan harus disetujui atau ditolak.")
        row = await self.repo.review(overtime_id, reviewer_emp, decision, (note or "").strip() or None)
        if row is None:
            raise _state("Pengajuan lembur ini sudah diperiksa atau tidak dapat diperiksa lagi.")
        return row

    # ------------------------------------------------------------------
    # Daftar lembur per SK & rekap bulanan
    # ------------------------------------------------------------------
    async def list_by_plan(self, user: CurrentUser, plan_id: UUID) -> Sequence[Any]:
        """Siapa pun yang dapat melihat SK dapat melihat lemburnya (anggota, PM, OPS, Finance)."""
        await check_plan_access(self.db, plan_id, user, PlanNeed.VIEW)
        return await self.repo.list_by_plan(plan_id, user.organization_id)

    async def recap(self, user: CurrentUser, month: date | None) -> Sequence[Any]:
        """Rekap per karyawan per bulan: Finance/OPS/Admin (review:overtime) seluruh organisasi;
        PM hanya unit yang dipegangnya (keputusan pemilik 2026-09-25, dok 10 V-28)."""
        if Permission.REVIEW_OVERTIME in user.permissions:
            return await self.repo.recap(user.organization_id, month, None)
        if RoleCode.PM in user.roles:
            return await self.repo.recap(user.organization_id, month, user.user_id)
        raise ForbiddenError("Rekap lembur hanya untuk Finance, OPS, Admin, atau PM unit.")
