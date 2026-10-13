"""
app/modules/work_plans/controllers/work_plan_controller.py

Controller orkestrasi use case manajemen rencana kerja (SK).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Depends
from fastapi.responses import HTMLResponse

from app.api.deps import (
    get_plan_assignment_service,
    get_plan_draft_service,
    get_plan_edit_service,
    get_plan_transition_service,
)
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
    WorkPlanCreate,
    WorkPlanResponse,
    WorkPlanUpdate,
)
from app.modules.work_plans.services.work_plan_service import (
    PlanAssignmentService,
    PlanDraftService,
    PlanEditService,
    PlanTransitionService,
    render_plan_preview_html,
)
from app.services.access_service import PlanAccess


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
        return await self.draft_service.driver_options(
            current_user, vehicle_id, candidate_ids, period_end, plan_id
        )

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
        return PlanDetailOut(
            **await self.draft_service.detail(plan_id, include_drafts=access.is_leader)
        )

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
        day_id = await self.edit_service.add_day(
            access, plan_id, data.work_date, data.title, data.sort_order
        )
        return PlanDayResponse(id=day_id, work_plan_id=plan_id, **data.model_dump())

    async def handle_add_task(
        self,
        day_id: UUID,
        data: PlanTaskCreate,
    ) -> PlanTaskResponse:
        """Menambahkan butir tugas pekerjaan ke dalam jadwal hari kerja."""
        task_id = await self.edit_service.add_task(day_id, data.title, data.sort_order)
        return PlanTaskResponse(
            id=task_id, work_plan_day_id=day_id, is_done=False, **data.model_dump()
        )

    async def handle_save_day(
        self,
        access: PlanAccess,
        day_id: UUID,
        data: DayPlanRequest,
    ) -> dict[str, object]:
        """Menyusun ulang judul dan daftar tugas hari kerja secara menyeluruh."""
        title, tasks = await self.edit_service.save_day(
            access, day_id, data.title, [t.title for t in data.tasks]
        )
        return {"id": str(day_id), "title": title, "tasks": tasks}


__all__ = ["WorkPlanController"]

