from datetime import date, datetime
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
    location_origin: str = "GPS"  # GPS, SIMULASI
    selfie_file_id: UUID | None = None
    face_result: str | None = None  # MATCH, NO_MATCH, LOW_QUALITY, SKIPPED
    face_similarity: float | None = None

class CheckOutRequest(BaseModel):
    location: GeoPoint
    location_origin: str = "GPS"

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
