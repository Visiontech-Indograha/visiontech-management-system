"""
app/modules/work_orders/controllers/work_order_controller.py

Controller untuk modul Work Orders.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.work_orders.dependencies import get_work_order_service
from app.modules.work_orders.schemas.work_order_schema import (
    PmCandidateOut,
    SurveySubmitIn,
    TeamSurveyOut,
    WorkOrderAssignSurvey,
    WorkOrderCreate,
    WorkOrderDetailOut,
    WorkOrderOut,
    WorkOrderSignBast,
)
from app.modules.work_orders.services.work_order_service import WorkOrderService


class WorkOrderController:
    """Controller use case Work Orders."""

    def __init__(self, service: WorkOrderService = Depends(get_work_order_service)) -> None:
        self.service = service

    async def list_work_orders(
        self,
        current_user: CurrentUser,
        division_id: UUID | None = None,
        status: str | None = None,
        client_id: UUID | None = None,
        pm_id: UUID | None = None,
        lead_team_id: UUID | None = None,
        q: str | None = None,
        limit: int = 50,
    ) -> list[WorkOrderOut]:
        rows = await self.service.list_work_orders(
            current_user,
            division_id=division_id,
            status=status,
            client_id=client_id,
            pm_id=pm_id,
            lead_team_id=lead_team_id,
            q=q,
            limit=limit,
        )
        return [
            WorkOrderOut(**(dict(r._mapping) if hasattr(r, "_mapping") else dict(r)))
            for r in rows
        ]

    async def list_pm_candidates(self, current_user: CurrentUser, division_id: UUID | None) -> list[PmCandidateOut]:
        rows = await self.service.list_pm_candidates(current_user, division_id)
        return [PmCandidateOut(**dict(r._mapping)) for r in rows]

    async def list_team_surveys(
        self, current_user: CurrentUser, *, scope_all: bool = False,
        date_from: date | None = None, date_to: date | None = None,
    ) -> list[TeamSurveyOut]:
        rows = await self.service.list_team_surveys(
            current_user, scope_all=scope_all, date_from=date_from, date_to=date_to
        )
        return [TeamSurveyOut(**(dict(r._mapping) if hasattr(r, "_mapping") else dict(r))) for r in rows]

    async def get_work_order(self, current_user: CurrentUser, work_order_id: UUID) -> WorkOrderDetailOut:
        data = await self.service.get_work_order(work_order_id, current_user)
        return WorkOrderDetailOut(**data)

    async def create_work_order(
        self, current_user: CurrentUser, data: WorkOrderCreate
    ) -> WorkOrderDetailOut:
        res = await self.service.create_work_order(data, current_user)
        return WorkOrderDetailOut(**res)

    async def assign_survey(
        self, current_user: CurrentUser, work_order_id: UUID, data: WorkOrderAssignSurvey
    ) -> WorkOrderDetailOut:
        res = await self.service.assign_survey(work_order_id, data, current_user)
        return WorkOrderDetailOut(**res)

    async def submit_survey(
        self, current_user: CurrentUser, work_order_id: UUID, data: SurveySubmitIn
    ) -> WorkOrderDetailOut:
        res = await self.service.submit_survey(work_order_id, data, current_user)
        return WorkOrderDetailOut(**res)

    async def apply_survey(
        self, current_user: CurrentUser, work_order_id: UUID
    ) -> WorkOrderDetailOut:
        res = await self.service.apply_survey(work_order_id, current_user)
        return WorkOrderDetailOut(**res)

    async def sign_bast(
        self, current_user: CurrentUser, work_order_id: UUID, data: WorkOrderSignBast
    ) -> WorkOrderDetailOut:
        res = await self.service.sign_bast(work_order_id, data, current_user)
        return WorkOrderDetailOut(**res)

    async def update_item_progress(
        self,
        current_user: CurrentUser,
        item_id: UUID,
        completed_qty: Decimal,
        status: str,
        photo_slots_snapshot: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        await self.service.update_item_progress(
            item_id, completed_qty, status, photo_slots_snapshot, current_user
        )
        return {"message": "Progres item berhasil diperbarui."}

    async def update_bom_actual(
        self,
        current_user: CurrentUser,
        bom_id: UUID,
        actual_qty: Decimal,
    ) -> dict[str, str]:
        await self.service.update_bom_actual(bom_id, actual_qty, current_user)
        return {"message": "Realisasi BOM berhasil diperbarui."}

    async def export_document(
        self, current_user: CurrentUser, work_order_id: UUID, template: str
    ) -> tuple[str, str, bytes]:
        return await self.service.build_export(work_order_id, template, current_user)
