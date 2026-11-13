"""Skema Pydantic untuk modul Work Orders (client_work_orders, surveys, items, dan bom)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

WorkOrderStatus = Literal[
    "WAITING_SURVEY",
    "SURVEY_IN_PROGRESS",
    "SURVEY_SUBMITTED",
    "READY_TO_EXECUTE",
    "IN_PROGRESS",
    "COMPLETED",
    "BAST_SIGNED",
    "CANCELLED",
]

ItemStatus = Literal["PENDING", "IN_PROGRESS", "DONE"]


# ── Work Order Items & BOM ──────────────────────────────────────────────────

class WorkOrderItemOut(BaseModel):
    item_id: UUID
    work_order_id: UUID
    survey_point_id: UUID | None = None
    work_type_id: UUID
    work_type_name: str | None = None
    title: str
    location_detail: str | None = None
    target_qty: Decimal = Decimal("1.0")
    completed_qty: Decimal = Decimal("0.0")
    photo_slots_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    status: ItemStatus = "PENDING"
    created_at: datetime


class WorkOrderBomOut(BaseModel):
    bom_id: UUID
    work_order_id: UUID
    work_order_item_id: UUID | None = None
    item_name: str
    unit: str = "pcs"
    estimated_qty: Decimal = Decimal("0.0")
    actual_qty: Decimal = Decimal("0.0")


# ── Survey Points & Surveys ─────────────────────────────────────────────────

class SurveyPointIn(BaseModel):
    point_name: str = Field(..., min_length=1, max_length=150)
    location_detail: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    recommended_work_type_id: UUID
    recommended_bom: list[dict[str, Any]] = Field(default_factory=list)
    remarks: str | None = None
    photos: list[dict[str, Any]] = Field(default_factory=list)


class SurveyPointOut(BaseModel):
    point_id: UUID
    work_order_id: UUID
    survey_id: UUID | None = None
    point_name: str
    location_detail: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    recommended_work_type_id: UUID | None = None
    recommended_work_type_name: str | None = None
    recommended_bom: list[dict[str, Any]] = Field(default_factory=list)
    remarks: str | None = None
    photos: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "TODO"


class SurveySubmitIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    narrative: str | None = None
    format: str = "CCTV"
    points: list[SurveyPointIn] = Field(default_factory=list)
    general_bom: list[dict[str, Any]] = Field(default_factory=list)


# ── Work Orders CRUD ────────────────────────────────────────────────────────

class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    client_id: UUID
    client_site_id: UUID | None = None
    division_id: UUID
    pm_id: UUID
    title: str = Field(..., min_length=3, max_length=200)
    initial_complaint: str | None = Field(None, max_length=2000)
    lead_team_id: UUID | None = None


class WorkOrderAssignSurvey(BaseModel):
    lead_team_id: UUID
    survey_date: date | None = Field(
        default=None, description="Tanggal survei (wajib diisi; kosong = 422 pesan awam); tim melihatnya di HP"
    )
    notes: str | None = Field(default=None, max_length=2000)


class WorkOrderSignBast(BaseModel):
    signer_name: str = Field(..., min_length=2, max_length=120)
    signature_data_uri: str | None = None
    notes: str | None = None


class WorkOrderOut(BaseModel):
    work_order_id: UUID
    wo_number: str
    client_id: UUID
    client_name: str | None = None
    client_site_id: UUID | None = None
    site_name: str | None = None
    site_address: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    division_id: UUID
    division_name: str | None = None
    pm_id: UUID
    pm_name: str | None = None
    lead_team_id: UUID | None = None
    team_name: str | None = None
    title: str
    initial_complaint: str | None = None
    status: WorkOrderStatus
    survey_assigned_at: datetime | None = None
    survey_submitted_at: datetime | None = None
    survey_approved_at: datetime | None = None
    bast_signed_at: datetime | None = None
    bast_signer_name: str | None = None
    leader_signed_at: datetime | None = None
    leader_signer_name: str | None = None
    total_items: int = 0
    completed_items: int = 0
    created_at: datetime


class WorkOrderDetailOut(WorkOrderOut):
    survey_assignment_summary: str | None = Field(
        default=None, description="Hanya terisi di respons assign-survey: 'Tim X akan melihat di HP pada tanggal Y'"
    )
    duplicate_title_warning: str | None = Field(
        default=None, description="Hanya terisi di respons pembuatan WO bila klien sama sudah punya WO berjudul sama"
    )
    survey_points: list[SurveyPointOut] = Field(default_factory=list)
    items: list[WorkOrderItemOut] = Field(default_factory=list)
    bom: list[WorkOrderBomOut] = Field(default_factory=list)


class TeamSurveyOut(BaseModel):
    """Survei work order aktif milik tim pemanggil (untuk HP ketua/anggota tim)."""

    survey_id: UUID
    work_order_id: UUID
    wo_number: str
    title: str
    client_name: str | None = None
    site_name: str | None = None
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    site_radius_m: int | None = None
    survey_date: date
    survey_status: str
    surveyor_team_id: UUID | None = None
    surveyor_team_name: str | None = None
    filled_points: int = 0


class PmCandidateOut(BaseModel):
    """Calon PM untuk form Buat Tugas Klien: hanya id, nama, dan divisi (tanpa kontak, email, atau peran)."""
    employee_id: UUID
    full_name: str
    division_id: UUID | None = None
    division_name: str | None = None
