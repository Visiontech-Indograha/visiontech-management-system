"""Skema form "Buat SK" alur v2 (flowchart SK2-A/B) dan notifikasi."""
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

PlanCategory = Literal["INSTALASI", "PEMELIHARAAN", "PERBAIKAN", "SURVEI", "LAINNYA"]


class FormPerson(BaseModel):
    id: UUID
    full_name: str
    position: str


class FormAsset(BaseModel):
    id: UUID
    kind: str
    vehicle_type: str | None = None
    code: str
    name: str


class FormSite(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    lat: float
    lng: float


class FormCategory(BaseModel):
    code: str
    label: str


class PlanFormOptions(BaseModel):
    unit_name: str | None
    categories: list[FormCategory]
    sites: list[FormSite]
    leaders: list[FormPerson]
    members: list[FormPerson]
    tools: list[FormAsset]
    vehicles: list[FormAsset]


class NewSiteInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class DraftTaskInput(BaseModel):
    title: str
    description: str
    file_ids: list[UUID] = []


class DraftDayInput(BaseModel):
    work_date: date
    tasks: list[DraftTaskInput]


class PlanDraftRequest(BaseModel):
    title: str
    description: str
    category: PlanCategory
    site_id: UUID | None = None
    new_site: NewSiteInput | None = None
    period_start: date
    period_end: date
    days: list[DraftDayInput]
    leader_employee_id: UUID
    member_employee_ids: list[UUID]
    tool_ids: list[UUID] = []
    vehicle_id: UUID | None = None
    driver_employee_id: UUID | None = None
    row_version: int | None = None   # wajib saat mengubah draf


class PlanDetailOut(BaseModel):
    plan: dict[str, Any]
    team: list[dict[str, Any]]
    days: list[dict[str, Any]]
    assets: list[dict[str, Any]]


class AmendmentRequest(BaseModel):
    row_version: int
    reason: str


class NotificationOut(BaseModel):
    id: UUID
    kind: str
    title: str
    body: str
    work_plan_id: UUID | None = None
    created_at: datetime
    read_at: datetime | None = None


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]
