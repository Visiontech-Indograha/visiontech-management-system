"""
app/services/overtime_service.py
Aturan bisnis lembur (V-28) — domain.js REPORT_OVERTIME (baris 607–614), REVIEW_OVERTIME (616–627).
Router tipis → service → repository; aturan bisnis di sini, SQL di repository.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.guards import PlanNeed, check_plan_access
from app.core.enums import PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import Permission
from app.repositories.org_clock_repo import OrgClockRepo
from app.repositories.overtime_repo import OvertimeRepo
from app.repositories.plan_access_repo import PlanAccessRepo


def _state(msg: str) -> AppError:
    return AppError("INVALID_STATE", msg, status=409)


class OvertimeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OvertimeRepo(db)

    # ------------------------------------------------------------------
    # domain.js REPORT_OVERTIME (baris 607–614)
    # ------------------------------------------------------------------
    async def report(self, user: CurrentUser, plan_id: UUID, hours: float, reason: str) -> Any:
        """Ketua atau anggota mengajukan lembur pada SK IN_PROGRESS."""
        # domain.js baris 611: hanya ketua atau anggota pekerjaan ini.
        access = await check_plan_access(self.db, plan_id, user, PlanNeed.LEADER_OR_MEMBER)

        # domain.js baris 608: hanya pekerjaan IN_PROGRESS.
        if access.plan.status != PlanStatus.IN_PROGRESS:
            raise _state("Hanya pekerjaan aktif yang bisa diajukan lembur.")

        # Tanggal dari server (V-10, domain.js memakai state.demoDate — bukan tanggal klien).
        today = (await OrgClockRepo(self.db).local_now(user.organization_id)).today

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
        """PM unit/OPS menyetujui atau menolak lembur yang masih PENDING_PM."""
        ot = await self.repo.get_for_review(overtime_id, user.organization_id)
        if ot is None:
            raise NotFoundError("Lembur")

        # domain.js baris 618: hanya yang masih PENDING_PM.
        if ot.status != "PENDING_PM":
            raise _state("Lembur tidak tersedia untuk direview.")

        # domain.js baris 620: can(actor, 'REVIEW_OVERTIME', unit) = PM unit SK, OPS, ADMIN.
        # Realisasi: cek plan.manages (PM unit / OPS / ADMIN) dari PlanAccessRepo.
        plan_access = await PlanAccessRepo(self.db).standing(
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

        row = await self.repo.review(overtime_id, reviewer_emp, decision, note or None)
        if row is None:
            raise _state("Lembur tidak tersedia untuk direview.")
        return row

    # ------------------------------------------------------------------
    # Daftar lembur per SK & rekap bulanan
    # ------------------------------------------------------------------
    async def list_by_plan(self, user: CurrentUser, plan_id: UUID) -> Sequence[Any]:
        """Siapa pun yang dapat melihat SK dapat melihat lemburnya (anggota, PM, OPS, Finance)."""
        await check_plan_access(self.db, plan_id, user, PlanNeed.VIEW)
        return await self.repo.list_by_plan(plan_id, user.organization_id)

    async def recap(self, user: CurrentUser, month: str | None) -> Sequence[Any]:
        """Rekap per karyawan per bulan — hanya yang punya izin review:overtime (Finance, OPS, Admin)."""
        if Permission.REVIEW_OVERTIME not in user.permissions:
            raise ForbiddenError("Hanya Finance, OPS, atau Admin yang dapat melihat rekap lembur.")
        return await self.repo.recap(user.organization_id, month)
