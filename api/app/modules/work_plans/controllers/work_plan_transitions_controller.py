"""
app/modules/work_plans/controllers/work_plan_transitions_controller.py

Controller orkestrasi use case transisi status rencana kerja (terbitkan, terima, banding, mulai, tutup).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db_with_user,
    get_plan_transition_service,
    get_signature_service,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    CompletionRequest,
    FinalReportOut,
    FinalReportSignatureOut,
    TransitionRequest,
    WorkPlanResponse,
)
from app.modules.work_plans.services.work_plan_service import (
    PlanTransitionService,
    SignatureService,
    html_to_pdf,
    render_final_report_html,
)
from app.services.access_service import PlanAccess, ensure_same_org


def _response(row: Any) -> WorkPlanResponse:
    """Fungsi pembantu memetakan baris database ke skema WorkPlanResponse."""
    return WorkPlanResponse(**row._mapping)


class WorkPlanTransitionsController:
    """Controller pengelolaan siklus hidup rencana kerja (publikasi, penerimaan, pelaksanaan, penutupan)."""

    def __init__(
        self,
        plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
        signature_service: SignatureService = Depends(get_signature_service),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> None:
        self.transition_service = plan_transition_service
        self.signature_service = signature_service
        self.db = db

    async def handle_get_signatures(
        self,
        plan_id: UUID,
    ) -> list[FinalReportSignatureOut]:
        """Mengambil daftar tanda tangan digital laporan akhir rencana kerja."""
        rows = await self.signature_service.final_report_signatures(plan_id)
        return [FinalReportSignatureOut(**r._mapping) for r in rows]

    async def handle_get_pdf(
        self,
        access: PlanAccess,
        plan_id: UUID,
    ) -> Response:
        """Mengunduh berkas biner PDF laporan akhir ber-QR code."""
        plan, signatures = await self.signature_service.final_report_with_qr(access.user, plan_id)
        pdf = await run_in_threadpool(html_to_pdf, render_final_report_html(plan, signatures))
        filename = f"{plan.number}-laporan-akhir.pdf".replace("/", "-")
        return Response(
            pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    async def handle_get_final_report(
        self,
        plan_id: UUID,
    ) -> FinalReportOut | None:
        """Mengambil data laporan akhir rencana kerja."""
        row = await self.transition_service.final_report(plan_id)
        return FinalReportOut(**row._mapping) if row else None

    async def handle_publish(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """PM menerbitkan rencana kerja."""
        plan = await self.transition_service.publish(
            plan_id, access.user.organization_id, access.user.user_id, data.row_version
        )
        return _response(plan)

    async def handle_accept(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """Ketua tim menerima rencana kerja yang diterbitkan."""
        plan = await self.transition_service.accept(
            plan_id, access.user.organization_id, access.user.user_id, data.row_version
        )
        return _response(plan)

    async def handle_appeal(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """Ketua tim mengajukan keberatan (banding) atas rencana kerja terbit."""
        plan = await self.transition_service.appeal(
            plan_id,
            access.user.organization_id,
            access.user.user_id,
            data.row_version,
            data.reason,
        )
        return _response(plan)

    async def handle_revise(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """PM membuka status revisi draf dari rencana kerja yang dibanding."""
        plan = await self.transition_service.revise(
            plan_id, access.user.organization_id, data.row_version
        )
        return _response(plan)

    async def handle_cancel(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """Membatalkan rencana kerja."""
        return _response(
            await self.transition_service.cancel_plan(
                plan_id, access.user.organization_id, data.row_version, data.reason
            )
        )

    async def handle_archive(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """Mengarsipkan (soft-delete) draf rencana kerja."""
        return _response(
            await self.transition_service.delete_plan(
                plan_id,
                access.user.organization_id,
                access.user.user_id,
                data.row_version,
                data.reason,
            )
        )

    async def handle_restore(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """Memulihkan draf rencana kerja terarsip."""
        return _response(
            await self.transition_service.restore_plan(
                plan_id, access.user.organization_id, data.row_version
            )
        )

    async def handle_start(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """Ketua tim memulai pelaksanaan pekerjaan rencana kerja."""
        plan = await self.transition_service.start(
            plan_id, access.user.organization_id, access.user.user_id, data.row_version
        )
        return _response(plan)

    async def handle_request_completion(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: CompletionRequest,
    ) -> WorkPlanResponse:
        """Ketua tim menyerahkan laporan akhir penugasan untuk diperiksa PM."""
        await ensure_same_org(self.db, access.user.organization_id, files=data.evidence_file_ids)
        return _response(
            await self.transition_service.request_complete(
                plan_id,
                access.user.organization_id,
                access.user.user_id,
                data.row_version,
                data.body,
                data.obstacle,
                data.evidence_file_ids,
            )
        )

    async def handle_approve_completion(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """PM menutup dan menyelesaikan rencana kerja setelah memeriksa laporan akhir."""
        return _response(
            await self.transition_service.approve_complete(
                plan_id,
                access.user.organization_id,
                access.user.user_id,
                data.row_version,
                data.reason,
            )
        )

    async def handle_return_completion(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: TransitionRequest,
    ) -> WorkPlanResponse:
        """PM mengembalikan laporan akhir kepada ketua tim untuk diperbaiki."""
        return _response(
            await self.transition_service.return_complete(
                plan_id,
                access.user.organization_id,
                access.user.user_id,
                data.row_version,
                data.reason,
            )
        )


__all__ = ["WorkPlanTransitionsController"]

