"""
app/schemas/plan_item.py
Skema data Pydantic untuk butir tugas rencana kerja (work_plan_item),
termasuk deteksi tabrakan jadwal (conflict detection), pembaruan progres,
dan alur rollover / PM Full Override.
"""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CheckConflictIn(BaseModel):
    """Permintaan pemeriksaan potensi tabrakan jadwal teknisi atau kendaraan."""
    work_date: date
    start_time: str = Field(..., description="Format HH:MM atau HH:MM:SS")
    end_time: str = Field(..., description="Format HH:MM atau HH:MM:SS")
    employee_ids: list[UUID] = Field(default_factory=list)
    vehicle_id: UUID | None = None
    exclude_item_id: UUID | None = None


class ConflictDetailOut(BaseModel):
    """Rincian item atau personel yang bertabrakan pada slot waktu."""
    conflict_type: str  # "EMPLOYEE" | "VEHICLE"
    entity_id: UUID
    entity_name: str
    conflicting_item_id: UUID
    conflicting_title: str
    start_time: str | None = None
    end_time: str | None = None


class CheckConflictOut(BaseModel):
    """Hasil deteksi tabrakan jadwal."""
    has_conflict: bool
    conflicts: list[ConflictDetailOut] = Field(default_factory=list)


class UpdateItemProgressIn(BaseModel):
    """Pembaruan progres pengerjaan tugas di lapangan."""
    completed_qty: float | None = None
    progress_percent: float | None = None
    status: str | None = None
    delay_reason: str | None = None


class UpdateItemProgressOut(BaseModel):
    """Respons pembaruan progres tugas."""
    item_id: UUID
    completed_qty: float
    progress_percent: float
    status: str
    delay_reason: str | None = None


class RequestRolloverIn(BaseModel):
    """Pengajuan pemindahan (rollover) tugas belum selesai ke hari berikutnya."""
    delay_reason: str = Field(..., min_length=3, description="Alasan kendala lapangan")
    target_daily_plan_id: UUID | None = None


class RequestRolloverOut(BaseModel):
    """Respons pengajuan rollover tugas."""
    item_id: UUID
    status: str
    rollover_approval_status: str
    delay_reason: str
    shifted_to_daily_id: UUID | None = None


class PmApproveOrMoveIn(BaseModel):
    """Tindakan PM (Full Override) untuk persetujuan rollover atau pemindahan slot."""
    action: str = Field(..., description="APPROVED | REJECTED | MOVE_SLOT")
    pm_override_reason: str = Field(..., min_length=2)
    target_daily_plan_id: UUID | None = None
    target_start_time: str | None = None
    target_end_time: str | None = None
    new_status: str | None = None


class PmApproveOrMoveOut(BaseModel):
    """Respons tindakan override PM."""
    success: bool
    action: str
    item_id: UUID
    new_item_id: UUID | None = None
    status: str
    rollover_approval_status: str
    message: str


class TaskChainItemDetailOut(BaseModel):
    """Rincian satu item tugas dalam satu rantai rollover."""
    item_id: UUID
    origin_item_id: UUID | None = None
    daily_plan_id: UUID
    work_date: str | None = None
    title: str
    task_phase: str = "MAIN_INSTALLATION"
    is_main_deliverable: bool = True
    depends_on_item_id: UUID | None = None
    target_qty: float
    completed_qty: float
    progress_percent: float
    status: str
    completion_id: UUID | None = None
    realization_photos_json: list[dict[str, Any]] = Field(default_factory=list)
    create_at: str | None = None


class TaskChainStatusOut(BaseModel):
    """Status agregasi seluruh rantai tugas (task chain) lintas hari dan lintas minggu."""
    root_item_id: UUID
    initial_total_target: float
    total_completed_across_weeks: float
    total_progress_percent: float
    is_eligible_for_completion: bool
    status_label: str
    existing_completion_id: UUID | None = None
    all_linked_item_ids: list[UUID] = Field(default_factory=list)
    items: list[TaskChainItemDetailOut] = Field(default_factory=list)


class GenerateCompletionIn(BaseModel):
    """Payload pembuatan Work Completion dari rantai tugas."""
    client_name: str | None = None
    project_title: str | None = None


class GenerateCompletionOut(BaseModel):
    """Respons hasil pembuatan / finalisasi Work Completion dari rantai tugas."""
    success: bool
    completion_id: UUID
    message: str
    total_target_unit: int
    order_status: str


__all__ = [
    "CheckConflictIn",
    "CheckConflictOut",
    "ConflictDetailOut",
    "GenerateCompletionIn",
    "GenerateCompletionOut",
    "PmApproveOrMoveIn",
    "PmApproveOrMoveOut",
    "RequestRolloverIn",
    "RequestRolloverOut",
    "TaskChainItemDetailOut",
    "TaskChainStatusOut",
    "UpdateItemProgressIn",
    "UpdateItemProgressOut",
]

