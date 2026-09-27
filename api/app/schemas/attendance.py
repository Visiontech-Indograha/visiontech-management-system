from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class SiteCreate(BaseModel):
    name: str
    address: str | None = None
    location: GeoPoint
    radius_m: int = Field(50, ge=10)

class SiteResponse(SiteCreate):
    id: UUID
    
class CheckInRequest(BaseModel):
    site_id: UUID
    location: GeoPoint
    location_origin: Literal["GPS", "SIMULASI"] = "GPS"  # MESIN hanya dari mesin absen, bukan API
    # Radius ketidakpastian GPS perangkat (m). Opsional: klien lama / antrean luring tidak ditolak (K-12).
    accuracy_m: float | None = Field(None, ge=0)
    selfie_file_id: UUID | None = None
    face_result: Literal["MATCH", "NO_MATCH", "LOW_QUALITY", "NOT_ENROLLED", "SKIPPED"] | None = None
    face_similarity: float | None = None

class CheckOutRequest(BaseModel):
    location: GeoPoint
    location_origin: Literal["GPS", "SIMULASI"] = "GPS"

class ExplanationRequest(BaseModel):
    explanation: str

class ReviewRequest(BaseModel):
    is_approved: bool
    note: str | None = None

class AttendanceResponse(BaseModel):
    id: UUID
    employee_id: UUID
    work_date: date
    site_id: UUID | None
    site_label: str
    check_in_at: datetime
    check_out_at: datetime | None
    distance_m: float
    is_late: bool
    is_early_leave: bool
    status: str
    explanation: str | None
    reviewed_at: datetime | None

class AttendanceListResponse(BaseModel):
    items: list[AttendanceResponse]
    total: int
    page: int
    size: int
    # O-10: tanggal hari ini menurut zona waktu organisasi — HP menandai "absensi hari ini" dengan ini,
    # bukan dengan jam perangkat (server yang memutuskan `work_date`).
    today: date | None = None
