from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID

class GeoPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class SiteCreate(BaseModel):
    name: str
    address: Optional[str] = None
    location: GeoPoint
    radius_m: int = Field(50, ge=10)

class SiteResponse(SiteCreate):
    id: UUID
    
class CheckInRequest(BaseModel):
    site_id: UUID
    location: GeoPoint
    location_origin: str = "GPS"  # GPS, SIMULASI
    selfie_file_id: Optional[UUID] = None
    face_result: Optional[str] = None  # MATCH, NO_MATCH, LOW_QUALITY, SKIPPED
    face_similarity: Optional[float] = None

class CheckOutRequest(BaseModel):
    location: GeoPoint
    location_origin: str = "GPS"

class ExplanationRequest(BaseModel):
    explanation: str

class ReviewRequest(BaseModel):
    is_approved: bool
    note: Optional[str] = None

class AttendanceResponse(BaseModel):
    id: UUID
    employee_id: UUID
    work_date: date
    site_id: Optional[UUID]
    site_label: str
    check_in_at: datetime
    check_out_at: Optional[datetime]
    distance_m: float
    is_late: bool
    is_early_leave: bool
    status: str
    explanation: Optional[str]
    reviewed_at: Optional[datetime]
