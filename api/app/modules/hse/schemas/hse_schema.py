"""
api/app/modules/hse/schemas/hse_schema.py

Skema Pydantic untuk modul HSE (Health, Safety & Environment / HES):
- Campaign K3 (edukasi, pengumuman, momen K3 terjadwal)
- Audit Pelacakan Pembaca (Tracking Acknowledgments & Cooldown)
- Inspeksi Keselamatan Kendaraan Lapangan (Vehicle Safety Inspections)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Aturan carousel kampanye K3 (foto + durasi baca). Ukuran per foto mengikuti batas unggah berkas (10 MB).
HSE_MAX_MEDIA = 8
HSE_MEDIA_MAX_BYTES = 10 * 1024 * 1024
HSE_MEDIA_MIMES = frozenset({"image/jpeg", "image/png", "image/webp"})
HSE_SECONDS_PER_MEDIA = 3
HSE_CAROUSEL_MIN_SECONDS = 10
HSE_CAROUSEL_MAX_SECONDS = 300


class HseCampaignBase(BaseModel):
    title: str = Field(..., max_length=255, description="Judul kampanye atau briefing K3")
    summary: str | None = Field(None, description="Ringkasan singkat kampanye")
    content_html: str = Field(..., description="Isi materi keselamatan (HTML/Markdown)")
    media_path: str | None = Field(None, max_length=255, description="Path foto banner atau infografis K3")
    media_paths: list[UUID] = Field(
        default_factory=list,
        max_length=HSE_MAX_MEDIA,
        description="Daftar id berkas foto (file_object) carousel K3, urutan tampil; maks 8",
    )
    target_audience: str = Field(default="ALL", description="Target audiens: ALL, FIELD, OFFICE, INDIVIDUAL")
    target_user_ids: list[UUID] | None = Field(
        default=None, description="Daftar user_id jika target_audience=INDIVIDUAL"
    )
    is_mandatory: bool = Field(default=True, description="Apakah wajib dibaca saat popup muncul")
    cooldown_seconds: int = Field(
        default=5,
        ge=0,
        le=300,
        description=(
            "Durasi wajib baca sebelum tombol konfirmasi aktif (detik). "
            "Dengan foto: 10-300 dan minimal 3 dtk per foto"
        ),
    )
    start_date: date = Field(..., description="Tanggal awal penayangan kampanye")
    end_date: date = Field(..., description="Tanggal akhir penayangan kampanye")
    is_active: bool = Field(default=True, description="Status keaktifan kampanye")


class HseCampaignCreate(HseCampaignBase):
    pass


class HseCampaignUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    summary: str | None = None
    content_html: str | None = None
    media_path: str | None = None
    media_paths: list[UUID] | None = Field(None, max_length=HSE_MAX_MEDIA)
    target_audience: str | None = None
    target_user_ids: list[UUID] | None = None
    is_mandatory: bool | None = None
    cooldown_seconds: int | None = Field(None, ge=0, le=300)
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


class HseCampaignResponse(HseCampaignBase):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    created_by_id: UUID
    creator_name: str | None = None
    total_readers: int = 0
    create_at: datetime
    update_at: datetime


class HseAcknowledgeCreate(BaseModel):
    platform: str = Field(default="web", description="Platform: web atau mobile")
    device_info: str | None = Field(None, max_length=255, description="Informasi perangkat klien")
    scroll_completed: bool = Field(
        default=True, description="Apakah user telah melakukan scroll hingga akhir materi"
    )
    read_duration_seconds: int = Field(default=0, ge=0, description="Total durasi waktu membaca dalam detik")


class HseReaderItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    acknowledgment_id: UUID
    campaign_id: UUID
    user_id: UUID
    full_name: str
    email: str
    employee_no: str | None = None
    platform: str
    device_info: str | None = None
    ip_address: str | None = None
    scroll_completed: bool
    read_duration_seconds: int
    acknowledged_at: datetime


class HseCampaignAuditStats(BaseModel):
    campaign_id: UUID
    title: str
    target_audience: str
    total_acknowledged: int
    readers: list[HseReaderItem]


class VehicleInspectionCreate(BaseModel):
    vehicle_id: UUID
    inspector_id: UUID | None = None
    period_type: str = Field(default="DAILY", description="DAILY, WEEKLY, MONTHLY")
    inspection_date: date | None = None
    odometer_km: int | None = Field(None, ge=0)
    checklist_json: dict[str, Any] = Field(
        default_factory=dict, description="Status checklist per item (rem, ban, oli, lampu, dll)"
    )
    photos_json: list[str] = Field(default_factory=list, description="Array URL/Path foto bukti inspeksi kendaraan")
    notes: str | None = None


class VehicleInspectionVerify(BaseModel):
    status: str = Field(..., description="VERIFIED atau REJECTED")
    notes: str | None = None


class VehicleInspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inspection_id: UUID
    vehicle_id: UUID
    vehicle_name: str | None = None
    number_plate: str | None = None
    inspector_id: UUID
    inspector_name: str | None = None
    period_type: str
    inspection_date: date
    odometer_km: int | None = None
    checklist_json: dict[str, Any]
    photos_json: list[str]
    notes: str | None = None
    status: str
    verified_by_id: UUID | None = None
    verifier_name: str | None = None
    verified_at: datetime | None = None
    create_at: datetime
