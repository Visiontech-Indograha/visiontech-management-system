"""
app/modules/work_completion/schemas/work_completion_schema.py

Pydantic schemas untuk entitas Order Proyek Klien (Work Completion) VMS V3.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _clean_coordinate(val: Any, max_abs: float) -> float | None:
    if val is None or val == "":
        return None
    if isinstance(val, str):
        val = val.replace(",", ".").strip()
        if not val:
            return None
    try:
        f = float(val)
    except (ValueError, TypeError):
        raise ValueError("Koordinat harus berupa angka desimal valid.") from None
    # Tanpa penskalaan diam-diam: 123 untuk latitude adalah galat masukan, bukan 0.000123.
    if abs(f) > max_abs:
        raise ValueError(f"Koordinat di luar batas jangkauan (-{max_abs} s/d {max_abs}).")
    return round(f, 7)


class WorkCompletionCreate(BaseModel):
    """Schema input pembuatan Order Klien baru oleh PM / OM."""
    division_id: UUID | None = None
    pm_id: UUID | None = None
    project_id: UUID | None = None
    client_id: UUID | None = Field(None, description="Klien dari master (wajib, kecuali lewat proyek)")
    project_title: str | None = Field(None, min_length=3, max_length=255, description="Judul (kosong = dari proyek)")
    order_number: str | None = Field(None, max_length=50, description="Nomor SPK / PO / WO")
    total_target_unit: int = Field(default=1, ge=1, description="Total target unit volume pekerjaan")
    unit_measure: str = Field(default="Unit", max_length=50, description="Satuan unit (Unit, Titik, Meter, Gardu)")
    order_status: str = Field(
        default="ONGOING", description="Status order (PENDING, ONGOING, URGENT, COMPLETED)", max_length=30
    )
    priority_level: str = Field(default="NORMAL", description="Prioritas (LOW, NORMAL, HIGH, URGENT)", max_length=20)
    site_address: str | None = Field(None, max_length=500)
    site_lat: float | None = None
    site_lng: float | None = None
    summary_notes: str | None = Field(None, max_length=2000)

    @field_validator("site_lat", mode="before")
    @classmethod
    def validate_site_lat(cls, v: Any) -> float | None:
        return _clean_coordinate(v, 90.0)

    @field_validator("site_lng", mode="before")
    @classmethod
    def validate_site_lng(cls, v: Any) -> float | None:
        return _clean_coordinate(v, 180.0)


class WorkCompletionUpdate(BaseModel):
    """Schema pembaruan detail Order Klien."""
    client_id: UUID | None = None
    project_title: str | None = Field(None, max_length=255)
    order_number: str | None = Field(None, max_length=50)
    total_target_unit: int | None = None
    unit_measure: str | None = Field(None, max_length=50)
    order_status: str | None = Field(None, max_length=30)
    priority_level: str | None = Field(None, max_length=20)
    site_address: str | None = Field(None, max_length=500)
    site_lat: float | None = None
    site_lng: float | None = None
    summary_notes: str | None = Field(None, max_length=2000)

    @field_validator("site_lat", mode="before")
    @classmethod
    def validate_site_lat(cls, v: Any) -> float | None:
        return _clean_coordinate(v, 90.0)

    @field_validator("site_lng", mode="before")
    @classmethod
    def validate_site_lng(cls, v: Any) -> float | None:
        return _clean_coordinate(v, 180.0)


class WorkCompletionAccDecision(BaseModel):
    """Schema keputusan ACC Client oleh PM."""
    decision: Literal["MENUNGGU_ACC", "DITERIMA", "DITOLAK_REWORK"]
    notes: str | None = Field(None, max_length=2000)


class WorkCompletionRevisionCreate(BaseModel):
    """Schema penambahan revisi permintaan dari klien."""
    description: str = Field(
        ..., min_length=3, description="Deskripsi permintaan revisi/tambahan klien", max_length=2000
    )
    request_date: date | None = None
    create_survey: bool = Field(default=False, description="Otomatis buat draf survei tugas untuk revisi ini")


class WorkCompletionRevisionOut(BaseModel):
    """Schema output revisi klien."""
    revision_id: UUID
    completion_id: UUID
    description: str
    request_date: date
    survey_task_id: UUID | None = None
    status: str
    created_by_id: UUID | None = None
    created_by_name: str | None = None
    create_at: Any | None = None


class WorkCompletionStatusUpdate(BaseModel):
    """Schema khusus pembaruan status order oleh PM/OM."""
    order_status: str = Field(..., description="PENDING, CANCELLED, ONGOING, URGENT, COMPLETED", max_length=30)
    notes: str | None = Field(None, max_length=2000)


class WorkCompletionSignRequest(BaseModel):
    """Schema tanda tangan digital Berita Acara Penyelesaian."""
    signature_data_url: str = Field(..., description="Base64 PNG tanda tangan digital", max_length=700000)
    summary_notes: str | None = Field(None, max_length=2000)
    obstacles: str | None = Field(None, max_length=2000)
    # Ketua tim: id file_object foto realisasi (kosong = tetap yang lama). Diabaikan saat PM menandatangani.
    realization_photos: list[UUID] = Field(default_factory=list, max_length=30)


class WorkCompletionVerifyOut(BaseModel):
    """Verifikasi publik dokumen resmi (QR): hanya data yang tercetak di dokumen."""
    completion_id: UUID
    order_number: str | None = None
    client_name: str | None = None
    project_title: str | None = None
    leader_signer_name: str | None = None
    leader_signed_at: datetime | None = None
    pm_signer_name: str | None = None
    pm_signed_at: datetime | None = None
    signature_hash: str
    intact: bool  # isi saat ini masih sama dengan saat disahkan


class WorkCompletionBomIn(BaseModel):
    """Schema input item Bon Material (BoM) untuk order proyek klien."""
    work_plan_item_id: UUID | None = None
    material_code: str | None = Field(None, max_length=50)
    material_name: str = Field(..., min_length=1, max_length=255)
    estimated_qty: float = Field(default=0.0, ge=0.0)
    actual_qty: float = Field(default=0.0, ge=0.0)
    unit: str = Field(default="Unit", max_length=50)
    category: str | None = Field(None, max_length=100)
    notes: str | None = Field(None, max_length=2000)
    sort_order: int = 0


class WorkCompletionBomUpdate(BaseModel):
    """Schema perbaikan item BoM (misal: input pemakaian riil actual_qty di lapangan)."""
    work_plan_item_id: UUID | None = None
    material_code: str | None = Field(None, max_length=50)
    material_name: str | None = Field(None, min_length=1, max_length=255)
    estimated_qty: float | None = Field(None, ge=0.0)
    actual_qty: float | None = Field(None, ge=0.0)
    unit: str | None = Field(None, max_length=50)
    category: str | None = Field(None, max_length=100)
    notes: str | None = Field(None, max_length=2000)
    sort_order: int | None = None


class WorkCompletionBomOut(BaseModel):
    """Schema output representasi item BoM."""
    bom_id: UUID
    completion_id: UUID
    work_plan_item_id: UUID | None = None
    material_code: str | None = None
    material_name: str
    estimated_qty: float
    actual_qty: float
    unit: str
    category: str | None = None
    notes: str | None = None
    sort_order: int = 0
    create_at: Any | None = None
    update_at: Any | None = None


class SyncBomFromWorkTypesIn(BaseModel):
    """Schema permintaan sinkronisasi otomatis BoM dari template jenis pekerjaan."""
    overwrite_existing: bool = False


class WorkCompletionOut(BaseModel):
    """Schema output representasi Order Proyek Klien."""
    completion_id: UUID
    project_id: UUID | None = None
    division_id: UUID | None = None
    division_name: str | None = None
    pm_id: UUID | None = None
    pm_name: str | None = None
    client_id: UUID | None = None
    client_name: str | None = None
    project_title: str
    order_number: str | None = None
    total_target_unit: int
    completed_target_unit: int = 0
    phases: list[str] = Field(default_factory=list)  # SURVEY/PREPARATION/INSTALLATION/REPLACEMENT/MAINTENANCE
    progress_pct: int = 0  # rata-rata dikerjakan/target per pekerjaan, 0–100
    unit_measure: str
    order_status: str
    priority_level: str
    acc_status: str = "MENUNGGU_ACC"
    acc_decided_at: Any | None = None
    acc_decided_by_id: UUID | None = None
    acc_decided_by_name: str | None = None
    acc_notes: str | None = None
    revisions: list[WorkCompletionRevisionOut] = Field(default_factory=list)
    start_work_date: Any | None = None
    end_work_date: Any | None = None
    site_address: str | None = None
    site_lat: float | None = None
    site_lng: float | None = None
    summary_notes: str | None = None
    obstacles: str | None = None
    realization_photos_json: list[dict[str, Any] | str] = Field(default_factory=list)
    bom_items: list[WorkCompletionBomOut] = Field(default_factory=list)
    leader_signer_id: UUID | None = None
    leader_signer_name: str | None = None
    leader_signed_at: Any | None = None
    pm_signer_id: UUID | None = None
    pm_signer_name: str | None = None
    pm_signed_at: Any | None = None
    signature_hash: str | None = None
    create_at: Any | None = None
    update_at: Any | None = None


class WorkCompletionListOut(BaseModel):
    """Schema pagination daftar Order Klien."""
    items: list[WorkCompletionOut]
    total: int
