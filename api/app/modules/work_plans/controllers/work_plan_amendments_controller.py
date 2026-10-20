"""
app/modules/work_plans/controllers/work_plan_amendments_controller.py

Controller orkestrasi use case adendum saat SK berjalan dan dokumen laporan akhir.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from fastapi.responses import HTMLResponse

from app.api.deps import get_plan_amendment_service, get_signature_service
from app.modules.work_plans.schemas.work_plan_schema import (
    AmendmentReasonIn,
    PlanChangeOut,
    PlanDetailOut,
    PlanDraftRequest,
)
from app.modules.work_plans.services.work_plan_service import (
    PlanAmendmentService,
    SignatureService,
    render_final_report_html,
)
from app.shared.access.access_service import PlanAccess


class WorkPlanAmendmentsController:
    """Controller proses pengajuan, evaluasi, penandatanganan adendum, dan laporan akhir."""

    def __init__(
        self,
        plan_amendment_service: PlanAmendmentService = Depends(get_plan_amendment_service),
        signature_service: SignatureService = Depends(get_signature_service),
    ) -> None:
        self.amendment_service = plan_amendment_service
        self.signature_service = signature_service

    async def handle_list_changes(
        self,
        plan_id: UUID,
    ) -> list[PlanChangeOut]:
        """Mengambil riwayat usulan perubahan adendum pada rencana kerja."""
        rows = await self.amendment_service.list_changes(plan_id)
        return [PlanChangeOut(**r._mapping) for r in rows]

    async def handle_request_amendment(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: AmendmentReasonIn,
    ) -> list[PlanChangeOut]:
        """Ketua tim mengajukan permohonan adendum saat rencana kerja sedang berjalan."""
        await self.amendment_service.request_amendment(access, data.reason)
        rows = await self.amendment_service.list_changes(plan_id)
        return [PlanChangeOut(**r._mapping) for r in rows]

    async def handle_reject_amendment(
        self,
        access: PlanAccess,
        plan_id: UUID,
        change_id: UUID,
        data: AmendmentReasonIn,
    ) -> list[PlanChangeOut]:
        """PM menolak usulan adendum dari ketua tim dengan memberikan alasan penolakan."""
        await self.amendment_service.reject_amendment(access, change_id, data.reason)
        rows = await self.amendment_service.list_changes(plan_id)
        return [PlanChangeOut(**r._mapping) for r in rows]

    async def handle_apply_amendment(
        self,
        access: PlanAccess,
        change_id: UUID,
        data: PlanDraftRequest,
    ) -> PlanDetailOut:
        """PM menyetujui usulan adendum dengan memperbarui isi dokumen rencana kerja."""
        result = await self.amendment_service.apply_amendment(access, change_id, data)
        return PlanDetailOut(**result)

    async def handle_accept_amendment(
        self,
        access: PlanAccess,
        plan_id: UUID,
        change_id: UUID,
    ) -> list[PlanChangeOut]:
        """Ketua menandatangani adendum yang disiapkan oleh PM."""
        await self.amendment_service.accept_amendment(access, change_id)
        rows = await self.amendment_service.list_changes(plan_id)
        return [PlanChangeOut(**r._mapping) for r in rows]

    async def handle_final_report_html(
        self,
        access: PlanAccess,
        plan_id: UUID,
    ) -> HTMLResponse:
        """Menghasilkan dokumen HTML A4 laporan akhir ber-tanda tangan QR."""
        plan, signatures = await self.signature_service.final_report_with_qr(access.user, plan_id)
        return HTMLResponse(render_final_report_html(plan, signatures))


__all__ = ["WorkPlanAmendmentsController"]
