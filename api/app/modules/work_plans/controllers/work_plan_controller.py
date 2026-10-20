"""
app/modules/work_plans/controllers/work_plan_controller.py

Controller orkestrasi use case manajemen rencana kerja (SK).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Depends
from fastapi.responses import HTMLResponse, Response

from app.api.deps import (
    get_plan_assignment_service,
    get_plan_draft_service,
    get_plan_edit_service,
    get_plan_transition_service,
)
from app.core.errors import AppError
from app.core.security import CurrentUser
from app.modules.work_plans.schemas.work_plan_schema import (
    AssignmentEmployeeOption,
    DayPlanRequest,
    FormAsset,
    FormPerson,
    FormSite,
    PlanAssignmentOptions,
    PlanDayCreate,
    PlanDayResponse,
    PlanDetailOut,
    PlanDraftRequest,
    PlanFormOptions,
    PlanTaskCreate,
    PlanTaskResponse,
    RescheduleItemRequest,
    RescheduleItemResponse,
    WorkPlanCreate,
    WorkPlanResponse,
    WorkPlanUpdate,
)
from app.modules.work_plans.services.plan_assignment_service import PlanAssignmentService
from app.modules.work_plans.services.plan_draft_service import PlanDraftService
from app.modules.work_plans.services.plan_edit_service import PlanEditService
from app.modules.work_plans.services.plan_transition_service import PlanTransitionService
from app.shared.access.access_service import PlanAccess
from app.shared.documents.document_export_service import DocumentExportService
from app.shared.documents.pdf_service import render_plan_preview_html


class WorkPlanController:
    """Controller use case pembuatan, penyuntingan draf, dan pengambilan data rencana kerja."""

    def __init__(
        self,
        plan_assignment_service: PlanAssignmentService = Depends(get_plan_assignment_service),
        plan_draft_service: PlanDraftService = Depends(get_plan_draft_service),
        plan_edit_service: PlanEditService = Depends(get_plan_edit_service),
        plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
    ) -> None:
        self.assignment_service = plan_assignment_service
        self.draft_service = plan_draft_service
        self.edit_service = plan_edit_service
        self.transition_service = plan_transition_service

    async def handle_assignment_options(
        self,
        current_user: CurrentUser,
        period_start: date,
        period_end: date,
    ) -> PlanAssignmentOptions:
        """Mengambil pilihan PM dan personel yang valid untuk periode SK baru."""
        values = await self.assignment_service.options(current_user, period_start, period_end)
        return PlanAssignmentOptions(
            can_choose_pm=values["can_choose_pm"],
            fixed_pm_employee_id=values["fixed_pm_employee_id"],
            fixed_unit_id=values["fixed_unit_id"],
            pm_options=[AssignmentEmployeeOption(**row._mapping) for row in values["pm_options"]],
            personnel_options=[AssignmentEmployeeOption(**row._mapping) for row in values["personnel_options"]],
        )

    async def handle_form_options(
        self,
        current_user: CurrentUser,
        plan_id: UUID | None = None,
    ) -> PlanFormOptions:
        """Mengambil pilihan master data untuk form pembuatan SK alur v2."""
        values = await self.draft_service.form_options(current_user, plan_id)
        return PlanFormOptions(
            unit_name=values["unit_name"],
            categories=values["categories"],
            sites=[FormSite(**r._mapping) for r in values["sites"]],
            leaders=[FormPerson(**r._mapping) for r in values["leaders"]],
            members=[FormPerson(**r._mapping) for r in values["members"]],
            tools=[FormAsset(**r._mapping) for r in values["tools"]],
            vehicles=[FormAsset(**r._mapping) for r in values["vehicles"]],
        )

    async def handle_driver_options(
        self,
        current_user: CurrentUser,
        vehicle_id: UUID,
        period_end: date,
        candidate_ids: list[UUID],
        plan_id: UUID | None = None,
    ) -> list[str]:
        """Mengambil calon pengemudi yang memiliki SIM dan tidak bentrok tugas."""
        return await self.draft_service.driver_options(current_user, vehicle_id, candidate_ids, period_end, plan_id)

    async def handle_create_full_plan(
        self,
        current_user: CurrentUser,
        data: PlanDraftRequest,
    ) -> PlanDetailOut:
        """Membuat dokumen SK lengkap dalam satu transaksi."""
        return PlanDetailOut(**await self.draft_service.create_plan(current_user, data))

    async def handle_get_plans(
        self,
        current_user: CurrentUser,
        status_filter: str | None = None,
        archived: bool = False,
    ) -> list[WorkPlanResponse]:
        """Mengambil daftar rencana kerja yang dapat diakses oleh pengguna."""
        await self.transition_service.start_due_plans(current_user.organization_id)
        rows = await self.edit_service.visible_plans(current_user, status_filter, archived)
        return [WorkPlanResponse(**row._mapping) for row in rows]

    async def handle_get_plan(
        self,
        access: PlanAccess,
    ) -> WorkPlanResponse:
        """Mengambil metadata dasar sebuah rencana kerja."""
        return WorkPlanResponse(**access.plan._mapping)

    async def handle_get_plan_detail(
        self,
        access: PlanAccess,
        plan_id: UUID,
    ) -> PlanDetailOut:
        """Mengambil seluruh detail rincian dokumen rencana kerja."""
        return PlanDetailOut(**await self.draft_service.detail(plan_id, include_drafts=access.is_leader))

    async def handle_edit_full_plan(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: PlanDraftRequest,
    ) -> PlanDetailOut:
        """Memperbarui seluruh data draf rencana kerja dalam satu transaksi."""
        return PlanDetailOut(**await self.draft_service.edit_draft(access.user, plan_id, data))

    async def handle_preview_plan(
        self,
        plan_id: UUID,
    ) -> HTMLResponse:
        """Menghasilkan pratinjau dokumen A4 HTML rencana kerja."""
        return HTMLResponse(render_plan_preview_html(await self.draft_service.detail(plan_id)))

    async def handle_export_plan(
        self,
        plan_id: UUID,
        format_type: str,
        inline: bool = False,
    ) -> Response:
        """Mengunduh atau menampilkan dokumen rencana kerja dalam format pilihan (PDF, DOCX, XLSX, PPTX)."""
        detail = await self.draft_service.detail(plan_id)
        number = (detail.get("plan", {}).get("number") or f"PLAN-{str(plan_id)[:8]}").replace("/", "-")

        fmt = format_type.lower()
        if fmt == "pdf":
            content = DocumentExportService.export_pdf(detail)
            media_type = "application/pdf"
            ext = "pdf"
        elif fmt == "docx":
            content = DocumentExportService.export_docx(detail)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        elif fmt == "xlsx":
            content = DocumentExportService.export_xlsx(detail)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        elif fmt == "pptx":
            content = DocumentExportService.export_pptx(detail)
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ext = "pptx"
        else:
            raise AppError("INVALID_FORMAT", f"Format {format_type} tidak didukung.", status=400)

        disposition = "inline" if inline else "attachment"
        filename = f"{number}.{ext}"

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
        )

    async def handle_create_plan(
        self,
        current_user: CurrentUser,
        data: WorkPlanCreate,
    ) -> WorkPlanResponse:
        """Membuat baris draf rencana kerja baru."""
        row = await self.edit_service.create(current_user, data)
        return WorkPlanResponse(
            **data.model_dump(),
            id=row.id,
            number=row.number,
            status=row.status,
            revision=row.revision,
            row_version=row.row_version,
            cancellation_reason=row.cancellation_reason,
        )

    async def handle_update_plan(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: WorkPlanUpdate,
    ) -> WorkPlanResponse:
        """Memperbarui kolom atribut draf rencana kerja."""
        updated = await self.edit_service.update(access, plan_id, data)
        return WorkPlanResponse(**updated._mapping)

    async def handle_add_day(
        self,
        access: PlanAccess,
        plan_id: UUID,
        data: PlanDayCreate,
    ) -> PlanDayResponse:
        """Menambahkan jadwal hari kerja ke dalam draf rencana kerja."""
        day_id = await self.edit_service.add_day(access, plan_id, data.work_date, data.title, data.sort_order)
        return PlanDayResponse(id=day_id, work_plan_id=plan_id, **data.model_dump())

    async def handle_add_task(
        self,
        day_id: UUID,
        data: PlanTaskCreate,
    ) -> PlanTaskResponse:
        """Menambahkan butir tugas pekerjaan ke dalam jadwal hari kerja."""
        task_id = await self.edit_service.add_task(day_id, data.title, data.sort_order)
        return PlanTaskResponse(id=task_id, work_plan_day_id=day_id, is_done=False, **data.model_dump())

    async def handle_save_day(
        self,
        access: PlanAccess,
        day_id: UUID,
        data: DayPlanRequest,
    ) -> dict[str, object]:
        """Menyusun ulang judul dan daftar tugas hari kerja secara menyeluruh."""
        title, tasks = await self.edit_service.save_day(access, day_id, data.title, [t.title for t in data.tasks])
        return {"id": str(day_id), "title": title, "tasks": tasks}

    async def handle_reschedule_item(
        self,
        current_user: CurrentUser,
        item_id: UUID,
        data: RescheduleItemRequest,
    ) -> RescheduleItemResponse:
        """Memindahkan / reschedule item penugasan ke slot waktu/hari lain (PM Full Override)."""
        res = await self.edit_service.reschedule_item(
            current_user,
            item_id,
            data.target_daily_plan_id,
            start_time=data.start_time,
            end_time=data.end_time,
            location_name=data.location_name,
            site_lat=data.site_lat,
            site_lng=data.site_lng,
            assigned_employee_ids=data.assigned_employee_ids,
        )
        return RescheduleItemResponse(
            item_id=res.item_id,
            daily_plan_id=res.daily_plan_id,
            weekly_plan_id=res.weekly_plan_id,
            title=res.title,
            start_time=str(res.start_time) if res.start_time else None,
            end_time=str(res.end_time) if res.end_time else None,
            location_name=res.location_name,
            status=res.status,
        )


__all__ = ["WorkPlanController"]
