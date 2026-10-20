"""
app/modules/work_plans/controllers/work_plan_changes_controller.py

Controller orkestrasi use case adendum perpanjangan waktu dan perubahan personel SK.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.work_plans.dependencies import get_plan_change_service
from app.modules.work_plans.schemas.work_plan_schema import (
    ChangeRequest,
    ChangeResponse,
    DecisionRequest,
)
from app.modules.work_plans.services.plan_change_service import PlanChangeService


async def _read(service: PlanChangeService, change_id: Any) -> ChangeResponse:
    """Fungsi pembantu membaca data perubahan SK dan memetakan ke ChangeResponse."""
    return ChangeResponse(**(await service.read(change_id))._mapping)


class WorkPlanChangesController:
    """Controller use case pengajuan, persetujuan, penerimaan, penolakan, dan penarikan adendum."""

    def __init__(
        self,
        plan_change_service: PlanChangeService = Depends(get_plan_change_service),
    ) -> None:
        self.service = plan_change_service

    async def handle_request_change(
        self,
        plan_id: UUID,
        current_user: CurrentUser,
        data: ChangeRequest,
    ) -> ChangeResponse:
        """Mengajukan usulan perpanjangan tanggal selesai atau pergantian susunan personel."""
        if data.type == "EXTEND":
            change_id = await self.service.request_change(plan_id, current_user, data.new_period_end, data.reason)
        else:
            change_id = await self.service.request_personnel_change(
                plan_id, current_user, data.leader_employee_id, data.member_employee_ids, data.reason
            )
        return await _read(self.service, change_id)

    async def handle_approve_change(
        self,
        change_id: UUID,
        current_user: CurrentUser,
        data: DecisionRequest,
    ) -> ChangeResponse:
        """PM unit / OPS menandatangani dan menyetujui usulan adendum."""
        return await _read(self.service, await self.service.approve_change(change_id, current_user))

    async def handle_accept_change(
        self,
        change_id: UUID,
        current_user: CurrentUser,
        data: DecisionRequest,
    ) -> ChangeResponse:
        """Ketua tim menandatangani dan mengaktifkan perubahan adendum."""
        return await _read(self.service, await self.service.accept_change(change_id, current_user))

    async def handle_reject_change(
        self,
        change_id: UUID,
        current_user: CurrentUser,
        data: DecisionRequest,
    ) -> ChangeResponse:
        """Menolak usulan adendum dengan mencantumkan alasan penolakan."""
        return await _read(
            self.service,
            await self.service.reject_change(change_id, current_user, data.reason),
        )

    async def handle_withdraw_change(
        self,
        change_id: UUID,
        current_user: CurrentUser,
        data: DecisionRequest,
    ) -> ChangeResponse:
        """PM menarik kembali usulan perubahan personel yang sebelumnya diajukan."""
        return await _read(
            self.service,
            await self.service.withdraw_change(change_id, current_user, data.reason),
        )


__all__ = ["WorkPlanChangesController"]
