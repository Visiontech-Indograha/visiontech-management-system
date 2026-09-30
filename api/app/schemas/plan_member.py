"""Skema permintaan & respons: plan member (dipindah dari api/v1/endpoints/work_plan_members.py, R-28 M2b)."""
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class TeamMemberOut(BaseModel):
    employee_id: str
    full_name: str
    position: str | None
    role_in_plan: str  # LEADER | MEMBER
    valid_from: date | None


class TeamRequest(BaseModel):
    leader_employee_id: UUID | None = None
    member_employee_ids: list[UUID] = Field(default_factory=list)
    row_version: int


class TeamResponse(BaseModel):
    leader_employee_id: str | None
    member_employee_ids: list[str]
    row_version: int
