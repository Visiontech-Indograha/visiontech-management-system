"""Skema permintaan & respons: plan change (dipindah dari api/v1/endpoints/work_plan_changes.py, R-28 M2b)."""
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChangeRequest(BaseModel):
    type: Literal["EXTEND", "PERSONNEL"]
    reason: str = ""
    new_period_end: date | None = None                        # EXTEND
    leader_employee_id: UUID | None = None                    # PERSONNEL
    member_employee_ids: list[UUID] = Field(default_factory=list)


class DecisionRequest(BaseModel):
    reason: str | None = None


class ChangeResponse(BaseModel):
    id: UUID
    work_plan_id: UUID
    change_type: str
    status: str
    reason: str
    decision_reason: str | None = None
