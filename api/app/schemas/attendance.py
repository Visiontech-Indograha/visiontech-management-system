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
    unit_id: UUID | None = None  # None = lokasi kantor; terisi = lokasi proyek unit itu (R-33)
    can_manage: bool = False  # peminta boleh mengelola (menghapus) lokasi ini
    
AttendanceChannel = Literal["MOBILE", "WEB"]


class CheckInRequest(BaseModel):
    site_id: UUID
    # Aplikasi pengirim. Default MOBILE agar APK lama tetap jalan; server mencocokkannya dengan
    # `employee.attendance_mode` (lapangan → HP, kantor → web) dan menolak bila tidak sesuai.
    channel: AttendanceChannel = "MOBILE"
    location: GeoPoint
    location_origin: Literal["GPS", "SIMULASI"] = "GPS"  # MESIN hanya dari mesin absen, bukan API
    # Radius ketidakpastian GPS perangkat (m). Opsional: klien lama / antrean luring tidak ditolak (K-12).
    accuracy_m: float | None = Field(None, ge=0)
    selfie_file_id: UUID | None = None
    face_result: Literal["MATCH", "NO_MATCH", "LOW_QUALITY", "NOT_ENROLLED", "SKIPPED"] | None = None
    face_similarity: float | None = None
    # R-33: wajib bila di luar radius lokasi atau saat mengajukan ulang absensi yang ditolak (dicek server).
    explanation: str | None = Field(None, max_length=1000)

class CheckOutRequest(BaseModel):
    channel: AttendanceChannel = "MOBILE"
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
    selfie_file_id: UUID | None = None
    # Hanya terisi di daftar GET /attendance:
    review_note: str | None = None  # alasan peninjau bila ditolak
    employee_name: str | None = None
    can_review: bool = False  # peminta berwenang meninjau baris ini (R-33, dihitung server)
    # R-34: absen luring — catatan pemeriksaan server & jam pulang yang menunggu persetujuan absen masuk.
    offline: bool = False
    offline_note: str | None = None
    check_out_requested_at: datetime | None = None

class AttendanceListResponse(BaseModel):
    items: list[AttendanceResponse]
    total: int
    page: int
    size: int
    # O-10: tanggal hari ini menurut zona waktu organisasi — HP menandai "absensi hari ini" dengan ini,
    # bukan dengan jam perangkat (server yang memutuskan `work_date`).
    today: date | None = None
    # R-34: jangkar waktu bertanda tangan server untuk absen luring (jam server saat ini, berlaku 30 hari).
    time_anchor: str | None = None


class DeviceKeyRequest(BaseModel):
    """Kunci publik EC P-256 (X.509 SubjectPublicKeyInfo DER, base64) dari Android Keystore."""
    device_id: str = Field(..., min_length=8, max_length=100)
    public_key: str = Field(..., min_length=40, max_length=1000)


class OfflineAttendanceEvent(BaseModel):
    """Satu absen luring: `payload` = JSON persis seperti yang ditandatangani HP; `signature` = ECDSA SHA-256
    (DER, base64). Swafoto diunggah lebih dulu; kecocokannya dicek lewat `selfie_sha256` di payload."""
    device_id: str = Field(..., min_length=8, max_length=100)
    client_op_id: UUID
    kind: Literal["CHECK_IN", "CHECK_OUT"]
    payload: str = Field(..., max_length=10000)
    signature: str = Field(..., max_length=500)
    selfie_file_id: UUID | None = None


class OfflineAttendanceResult(BaseModel):
    client_op_id: UUID
    result: str  # status absen masuk (AUTO_VALID/NEEDS_REVIEW) atau CHECKED_OUT / CHECK_OUT_PENDING_REVIEW
    attendance_id: UUID | None
    duplicate: bool
    event_time: datetime | None = None
    time_trusted: bool | None = None
    notes: list[str] = []


# ── Dipindah dari api/v1/endpoints/attendance_cron.py (R-28 M2b) ──
class MissingCheckInResponse(BaseModel):
    alerted: bool
    check_ins_today: int


class NeedsReviewResponse(BaseModel):
    alerted: bool
    needs_review_today: int
    daily_average: float
