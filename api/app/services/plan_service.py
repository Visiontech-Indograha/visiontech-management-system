"""
app/services/plan_service.py
Aturan bisnis siklus SK (Surat Keputusan).
Padanan langsung domain.js → transition() di prototipe VMS.

Setiap method:
  1. Ambil plan dari repo (lempar NotFoundError bila tidak ada)
  2. Validasi status (lempar InvalidStateError bila tidak cocok)
  3. Jalankan aksi
  4. Kembalikan plan yang sudah diperbarui
"""
from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, InvalidStateError, ConflictError, ForbiddenError
from app.repositories.plan_repo import PlanRepo
from app.repositories.user_repo import UserRepo
from app.services.document_service import DocumentService


# Status yang valid sebelum transisi bisa terjadi
_VALID_BEFORE: dict[str, str] = {
    "publish": "DRAFT",
    "accept":  "PUBLISHED",
    "start":   "ACCEPTED",
    "complete":"IN_PROGRESS",
    "cancel":  None,  # bisa dari berbagai status
}


class PlanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PlanRepo(db)
        self.user_repo = UserRepo(db)
        self.doc_svc = DocumentService(db)

    async def _get_or_404(self, plan_id: UUID, org_id: UUID):
        plan = await self.repo.get_by_id(plan_id, org_id)
        if not plan:
            raise NotFoundError("SK")
        return plan

    async def publish(
        self,
        plan_id: UUID,
        org_id: UUID,
        user_id: UUID,
        row_version: int,
    ) -> dict:
        """
        DRAFT → PUBLISHED.
        Buat snapshot + SHA-256 + nomor seri + insert plan_document.
        """
        plan = await self._get_or_404(plan_id, org_id)
        if plan.status != "DRAFT":
            raise InvalidStateError(
                f"Hanya SK berstatus DRAFT yang bisa diterbitkan. Status saat ini: {plan.status}."
            )

        emp_id = await self.user_repo.get_employee_id(user_id)
        if not emp_id:
            raise ForbiddenError("Akun Anda tidak terhubung ke data karyawan.")

        updated = await self.repo.update_status(
            plan_id, "PUBLISHED", row_version,
            extra_fields={"published_at": "now()"},
        )
        if not updated:
            raise ConflictError()

        doc_info = await self.doc_svc.register_document_snapshot(
            plan_id=plan_id,
            org_id=org_id,
            issued_by_employee_id=emp_id,
            kind="SK",
            version=updated.revision if hasattr(updated, "revision") else 1,
        )
        return {"plan": dict(updated._mapping), "document": doc_info}

    async def accept(
        self,
        plan_id: UUID,
        org_id: UUID,
        user_id: UUID,
        row_version: int,
    ) -> dict:
        """PUBLISHED → ACCEPTED. Hanya leader yang boleh."""
        plan = await self._get_or_404(plan_id, org_id)
        if plan.status != "PUBLISHED":
            raise InvalidStateError(
                f"Hanya SK berstatus PUBLISHED yang bisa diterima. Status saat ini: {plan.status}."
            )
        # Cek apakah user adalah leader SK ini
        is_leader = await self.repo.scalar(
            "SELECT vms.is_plan_leader(:plan, :user)",
            {"plan": plan_id, "user": user_id},
        ) if hasattr(self.repo, 'scalar') else False

        if not is_leader:
            raise ForbiddenError("Hanya ketua SK yang dapat menerima penugasan ini.")

        updated = await self.repo.update_status(
            plan_id, "ACCEPTED", row_version,
            extra_fields={"accepted_at": "now()"},
        )
        if not updated:
            raise ConflictError()
        return dict(updated._mapping)

    async def start(
        self, plan_id: UUID, org_id: UUID, row_version: int
    ) -> dict:
        """ACCEPTED → IN_PROGRESS."""
        plan = await self._get_or_404(plan_id, org_id)
        if plan.status != "ACCEPTED":
            raise InvalidStateError(
                f"SK harus berstatus ACCEPTED sebelum bisa dimulai. Status saat ini: {plan.status}."
            )
        updated = await self.repo.update_status(
            plan_id, "IN_PROGRESS", row_version,
            extra_fields={"started_at": "now()"},
        )
        if not updated:
            raise ConflictError()
        return dict(updated._mapping)

    async def request_completion(
        self, plan_id: UUID, org_id: UUID, row_version: int
    ) -> dict:
        """IN_PROGRESS → COMPLETION_REVIEW."""
        plan = await self._get_or_404(plan_id, org_id)
        if plan.status != "IN_PROGRESS":
            raise InvalidStateError(
                f"SK harus berstatus IN_PROGRESS untuk mengajukan penyelesaian."
            )
        updated = await self.repo.update_status(
            plan_id, "COMPLETION_REVIEW", row_version
        )
        if not updated:
            raise ConflictError()
        return dict(updated._mapping)

    async def approve_completion(
        self, plan_id: UUID, org_id: UUID, row_version: int
    ) -> dict:
        """COMPLETION_REVIEW → COMPLETED."""
        plan = await self._get_or_404(plan_id, org_id)
        if plan.status != "COMPLETION_REVIEW":
            raise InvalidStateError(
                "SK harus dalam status COMPLETION_REVIEW untuk disetujui selesai."
            )
        updated = await self.repo.update_status(
            plan_id, "COMPLETED", row_version,
            extra_fields={"completed_at": "now()"},
        )
        if not updated:
            raise ConflictError()
        return dict(updated._mapping)

    async def cancel(
        self, plan_id: UUID, org_id: UUID, row_version: int, reason: str
    ) -> dict:
        """* → CANCELLED. Tidak bisa dari COMPLETED."""
        plan = await self._get_or_404(plan_id, org_id)
        if plan.status == "COMPLETED":
            raise InvalidStateError("SK yang sudah selesai tidak dapat dibatalkan.")
        updated = await self.repo.update_status(
            plan_id, "CANCELLED", row_version,
            extra_fields={"cancel_reason": reason, "cancelled_at": "now()"},
        )
        if not updated:
            raise ConflictError()
        return dict(updated._mapping)
