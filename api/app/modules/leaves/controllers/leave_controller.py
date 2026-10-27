"""
app/modules/leaves/controllers/leave_controller.py

Controller untuk use case pengajuan cuti & sakit karyawan.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.leaves.dependencies import get_leave_service
from app.modules.leaves.schemas.leave_schema import (
    LeaveBalanceResponse,
    LeaveCreate,
    LeaveResponse,
    LeaveReview,
)
from app.modules.leaves.services.leave_service import LeaveService


def _response(row: Any) -> LeaveResponse:
    return LeaveResponse(**row._mapping)


class LeaveController:
    """Controller use case cuti dan izin."""

    def __init__(self, service: LeaveService = Depends(get_leave_service)) -> None:
        self.service = service

    async def handle_apply(self, user: CurrentUser, data: LeaveCreate) -> LeaveResponse:
        return _response(await self.service.apply(user, data))

    async def handle_review(self, user: CurrentUser, leave_id: UUID, data: LeaveReview) -> LeaveResponse:
        return _response(await self.service.review(user, leave_id, data))

    async def handle_get(self, leave_id: UUID) -> LeaveResponse:
        return _response(await self.service.get(leave_id))

    async def handle_list(
        self,
        employee_id: UUID | None = None,
        status: str | None = None,
        year: int | None = None,
    ) -> list[LeaveResponse]:
        rows = await self.service.list(employee_id=employee_id, status=status, year=year)
        return [_response(r) for r in rows]

    async def handle_balance(self, employee_id: UUID, year: int) -> LeaveBalanceResponse:
        bal = await self.service.balance(employee_id, year)
        return LeaveBalanceResponse(
            balance_id=bal.balance_id,
            employee_id=bal.employee_id,
            employee_name="",
            period_year=bal.period_year,
            total_quota=bal.total_quota,
            used_quota=bal.used_quota,
            remaining_quota=bal.remaining_quota,
        )
