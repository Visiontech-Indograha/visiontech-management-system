"""
api/app/modules/hse/schemas/hse_schema.py

Skema Pydantic untuk modul HSE (Health, Safety & Environment / HES):
- Campaign K3 (edukasi, pengumuman, momen K3 terjadwal)
- Audit Pelacakan Pembaca (Tracking Acknowledgments & Cooldown)
- Inspeksi Keselamatan Kendaraan Lapangan (Vehicle Safety Inspections)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Aturan carousel kampanye K3 (foto + durasi baca). Ukuran per foto mengikuti batas unggah berkas (10 MB).
HSE_MAX_MEDIA = 8
HSE_MEDIA_MAX_BYTES = 10 * 1024 * 1024
HSE_MEDIA_MIMES = frozenset({"image/jpeg", "image/png", "image/webp"})
HSE_SECONDS_PER_MEDIA = 3
HSE_CAROUSEL_MIN_SECONDS = 10
HSE_CAROUSEL_MAX_SECONDS = 300
HSE_CAPTION_MAX_CHARS = 300


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
    media_captions: list[str] = Field(
        default_factory=list,
        max_length=HSE_MAX_MEDIA,
        description="Keterangan teks per foto (sejajar media_paths), maks 300 karakter per foto",
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
    media_captions: list[str] | None = Field(None, max_length=HSE_MAX_MEDIA)
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


# Batas input inspeksi kendaraan (web dan HP wajib sama).
INSPECTION_PERIOD_PATTERN = "^(DAILY|WEEKLY|MONTHLY)$"
INSPECTION_VERIFY_PATTERN = "^(VERIFIED|REJECTED)$"
INSPECTION_STATUS_PATTERN = "^(SUBMITTED|VERIFIED|REJECTED)$"
INSPECTION_MAX_CHECKLIST = 60
INSPECTION_MAX_PHOTOS = 10
INSPECTION_MAX_NOTES = 1000
INSPECTION_MAX_ODOMETER = 10_000_000


class VehicleInspectionCreate(BaseModel):
    vehicle_id: UUID
    inspector_id: UUID | None = None
    period_type: str = Field(default="DAILY", pattern=INSPECTION_PERIOD_PATTERN,
                             description="DAILY, WEEKLY, MONTHLY")
    inspection_date: date | None = None
    odometer_km: int | None = Field(None, ge=0, le=INSPECTION_MAX_ODOMETER)
    checklist_json: dict[str, Any] = Field(
        default_factory=dict, max_length=INSPECTION_MAX_CHECKLIST,
        description="Status per butir; butir baku: GET /hse/inspections/checklist-template",
    )
    photos_json: list[Annotated[str, StringConstraints(max_length=255)]] = Field(
        default_factory=list, max_length=INSPECTION_MAX_PHOTOS,
        description="ID berkas foto bukti (hasil POST /files/upload), maks 10",
    )
    notes: str | None = Field(None, max_length=INSPECTION_MAX_NOTES)


class VehicleInspectionVerify(BaseModel):
    status: str = Field(..., pattern=INSPECTION_VERIFY_PATTERN, description="VERIFIED atau REJECTED")
    notes: str | None = Field(None, max_length=INSPECTION_MAX_NOTES)


class InspectionChecklistItem(BaseModel):
    key: str
    label: str
    options: list[str]


class InspectionChecklistTemplate(BaseModel):
    period_types: list[str]
    items: list[InspectionChecklistItem]


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
