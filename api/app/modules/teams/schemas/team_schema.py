"""
app/modules/teams/schemas/team_schema.py
Skema data Pydantic untuk Tim Operasional dan Anggota Tim.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Prefiks API (app.main.API_PREFIX); logo_url dibentuk dari sini agar selalu bisa diunduh klien.
TEAM_LOGO_PATH = "/api/v1/teams/{team_id}/logo"


class MemberAdd(BaseModel):
    employee_id: UUID


class MemberOut(BaseModel):
    member_id: UUID
    team_id: UUID
    employee_id: UUID
    full_name: str | None = None
    employee_no: str | None = None
    phone_number: str | None = None
    system_role: str | None = None
    photo_file_id: UUID | None = None
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
    logo_file_id: UUID | None = None
    logo_url: str | None = None

    @model_validator(mode="after")
    def _logo_url(self) -> TeamListItem:
        if self.logo_file_id is not None and self.logo_url is None:
            self.logo_url = TEAM_LOGO_PATH.format(team_id=self.team_id)
        return self


class TeamDetail(TeamListItem):
    members: list[MemberOut] = []


class TeamLogoOut(BaseModel):
    team_id: UUID
    logo_file_id: UUID
    logo_url: str
