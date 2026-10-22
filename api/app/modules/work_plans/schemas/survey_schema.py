"""
app/modules/work_plans/schemas/survey_schema.py
Survei ACS & CCTV berformat baku (docs/37). Tugas survei = item fase SURVEY dari PM (menempel pada order);
titik = item fase SURVEY buatan ketua tim (depends_on = tugas); material/kebutuhan/kabel per titik =
work_completion_bom (work_plan_item_id = titik, category).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

SurveyFormat = Literal["ACS", "CCTV"]
LineCategory = Literal["MATERIAL", "KEBUTUHAN", "KABEL"]
SurveyState = Literal["DRAFT", "SUBMITTED", "APPROVED"]
FollowPhase = Literal["PREPARATION", "INSTALLATION", "REPLACEMENT", "MAINTENANCE"]
PointStatus = Literal["EXISTING", "PROPOSED"]  # sudah terpasang / usulan pemasangan baru


class PointPhoto(BaseModel):
    file_id: UUID
    requirement_id: UUID  # slot foto (image_requirement), mis. Tampak Luar / View CCTV Camera


class PointLine(BaseModel):
    """Satu baris per titik: MATERIAL (masuk BoM), KEBUTUHAN (alat/izin: scaffolding, tangga, grounding),
    KABEL (ukuran instalasi CCTV per kamera: galian, kabel FO, kabel power, subduct, pipa, …)."""

    category: LineCategory = "MATERIAL"
    name: str = Field(min_length=1, max_length=255)
    qty: Decimal = Field(Decimal("1"), ge=0, le=Decimal("99999999"))
    unit: str = Field("Unit", min_length=1, max_length=50)
    notes: str | None = Field(None, max_length=500)


class PointIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)  # "Pintu akses Samping", "Titik Pemasangan CCTV 03"
    point_type_id: UUID | None = None  # jenis titik (work type SURVEY_POINT); kosong = jenis bawaan survei
    point_status: PointStatus = "PROPOSED"
    remarks: list[str] = Field(default_factory=list, max_length=20)
    photos: list[PointPhoto] = Field(default_factory=list, max_length=10)
    lines: list[PointLine] = Field(default_factory=list, max_length=60)
    site_lat: Decimal | None = Field(default=None, ge=-90, le=90)
    site_lng: Decimal | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _clean(self) -> PointIn:
        self.remarks = [r.strip() for r in self.remarks if r.strip()]
        return self


class ReportIn(BaseModel):
    """Bagian tingkat laporan yang diisi ketua tim: narasi, tujuan, lokasi, gambar layout."""

    narrative: str | None = Field(None, max_length=4000)
    purpose: str | None = Field(None, max_length=255)
    location: str | None = Field(None, max_length=500)


class LineEditIn(BaseModel):
    """Ubah satu baris BoM (ketua tim saat draf, PM saat meninjau)."""

    name: str = Field(min_length=1, max_length=255)
    qty: Decimal = Field(ge=0, le=Decimal("99999999"))
    unit: str = Field(min_length=1, max_length=50)


class CatalogAddIn(BaseModel):
    """PM menyimpan material di luar katalog ke katalog jenis titik."""

    point_type_id: UUID
    name: str = Field(min_length=1, max_length=255)
    unit: str = Field(min_length=1, max_length=50)


class ReviewIn(BaseModel):
    decision: Literal["APPROVE", "RETURN"]
    note: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def _note(self) -> ReviewIn:
        if self.decision == "RETURN" and not (self.note or "").strip():
            raise ValueError("Tulis catatan perbaikan untuk ketua tim.")
        return self


class PointLocationIn(BaseModel):
    site_lat: Decimal = Field(ge=-90, le=90)
    site_lng: Decimal = Field(ge=-180, le=180)


class PlanFromSurveyIn(BaseModel):
    """Susun item lanjutan dari survei yang disetujui pada jadwal DRAFT/SUBMITTED tim yang sama."""

    daily_plan_id: UUID | None = None  # jadwal DRAFT/SUBMITTED yang sudah ada, atau
    work_date: date | None = None  # tanggal: jadwal DRAFT tim dibuat otomatis bila belum ada
    work_type_id: UUID | None = None  # kosong = pemasangan lanjutan bawaan tiap jenis titik
    task_phase: FollowPhase = "INSTALLATION"
    point_ids: list[UUID] = Field(default_factory=list, max_length=100)  # kosong = semua titik
    preparation_work_type_id: UUID | None = None  # bila diisi: item PREPARATION untuk titik yang punya KEBUTUHAN


class SlotOut(BaseModel):
    requirement_id: UUID
    name: str
    mandatory: bool
    hint: str | None = None
    example_file_id: str | None = None  # foto panduan pengambilan gambar dari PM


class CatalogOut(BaseModel):
    name: str
    unit: str
    category: str | None = None
    default_qty: Decimal = Decimal("1")


class PointTypeOut(BaseModel):
    """Jenis titik yang boleh dipakai survei ini: slot foto & katalog material sendiri."""

    work_type_id: UUID
    name: str
    slots: list[SlotOut]
    catalog: list[CatalogOut]
    follow_up_work_type_id: UUID | None = None


class LineOut(PointLine):
    bom_id: UUID
    custom: bool = False  # material di luar katalog jenis titiknya — diperiksa PM


class PhotoOut(BaseModel):
    file_id: UUID
    requirement_id: UUID | None = None
    slot: str | None = None


class PointOut(BaseModel):
    point_id: UUID
    name: str
    remarks: list[str]
    photos: list[PhotoOut]
    lines: list[LineOut]
    site_lat: Decimal | None = None
    site_lng: Decimal | None = None
    update_at: datetime
    point_type_id: UUID
    point_type_name: str
    point_status: PointStatus = "PROPOSED"


class BomRow(BaseModel):
    group: str  # nama jenis titik, atau "Umum" untuk material umum lokasi
    name: str
    qty: Decimal
    unit: str
    custom: bool = False


class SurveyOut(BaseModel):
    task_id: UUID
    daily_plan_id: UUID
    work_date: date
    plan_status: str
    team_id: UUID | None = None
    team_name: str | None = None
    division_id: UUID
    division_name: str
    format: SurveyFormat
    work_type_id: UUID
    work_type_name: str
    completion_id: UUID
    client_name: str
    project_title: str
    location: str | None = None
    purpose: str | None = None
    narrative: str | None = None
    state: SurveyState
    review_note: str | None = None
    point_types: list[PointTypeOut]
    points: list[PointOut]
    general_lines: list[LineOut] = []  # material umum lokasi (rack, panel, kabel tray utama, …)
    bom: list[BomRow]  # MATERIAL per jenis titik + umum
    can_edit_bom: bool = False  # ketua tim saat draf, PM saat meninjau
    can_edit: bool  # ketua tim, jadwal berjalan, belum dikirim
    can_review: bool  # PM/OM divisi, sudah dikirim
    can_move: bool = False  # boleh menggeser titik di peta layout


class SurveyListItem(BaseModel):
    task_id: UUID
    title: str
    state: SurveyState
    format: SurveyFormat
    work_date: date
    plan_status: str
    daily_plan_id: UUID
    division_id: UUID
    division_name: str
    team_name: str | None = None
    work_type_name: str
    completion_id: UUID
    client_name: str
    project_title: str
    site_address: str | None = None
    point_count: int
    update_at: datetime


class PlanFromSurveyOut(BaseModel):
    daily_plan_id: UUID
    created_item_ids: list[UUID]
