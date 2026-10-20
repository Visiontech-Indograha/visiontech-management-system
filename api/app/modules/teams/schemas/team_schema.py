"""
app/modules/teams/schemas/team_schema.py
Skema data Pydantic untuk Tim Operasional dan Anggota Tim.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MemberAdd(BaseModel):
    employee_id: UUID


class MemberOut(BaseModel):
    member_id: UUID
    team_id: UUID
    employee_id: UUID
    full_name: str | None = None
    employee_no: str | None = None
    system_role: str | None = None
    is_active: bool
    create_at: datetime


class TeamCreate(BaseModel):
    office_id: UUID
    division_id: UUID
    leader_employee_id: UUID
    name: str = Field(..., min_length=2, max_length=150)
    status: bool = True


class TeamUpdate(BaseModel):
    office_id: UUID | None = None
    division_id: UUID | None = None
    leader_employee_id: UUID | None = None
    name: str | None = Field(None, min_length=2, max_length=150)
    status: bool | None = None


class TeamListItem(BaseModel):
    team_id: UUID
    office_id: UUID
    division_id: UUID
    leader_employee_id: UUID
    leader_name: str | None = None
    division_name: str | None = None
    office_name: str | None = None
    name: str
    status: bool
    member_count: int = 0
    create_at: datetime


class TeamDetail(TeamListItem):
    members: list[MemberOut] = []
