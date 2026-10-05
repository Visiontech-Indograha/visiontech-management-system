"""
app/schemas/attendance.py

Request and response schemas for employee attendance and site locations.
Handles check-ins, check-outs, offline attendance events, and reviews.
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    """
    Schema for geographic coordinates (latitude and longitude).
    """
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class SiteCreate(BaseModel):
    """
    Schema for creating a new work site.
    """
    name: str
    address: str | None = None
    location: GeoPoint
    radius_m: int = Field(50, ge=10)


class SiteResponse(SiteCreate):
    """
    Schema representing a work site in the system.
    """
    id: UUID
    # None = lokasi kantor; terisi = lokasi proyek unit itu (R-33)
    unit_id: UUID | None = None
    # Menandakan apakah peminta boleh mengelola atau menghapus lokasi ini
    can_manage: bool = False

AttendanceChannel = Literal["MOBILE", "WEB"]


class CheckInRequest(BaseModel):
    """
    Schema for processing a check-in request.
    """
    site_id: UUID
    # Aplikasi pengirim. Default MOBILE agar APK lama tetap jalan; server mencocokkannya dengan
    # `employee.attendance_mode` (lapangan → HP, kantor → web) dan menolak bila tidak sesuai.
    channel: AttendanceChannel = "MOBILE"
    location: GeoPoint
    # MESIN hanya digunakan untuk absen dari mesin fisik, bukan API
    location_origin: Literal["GPS", "SIMULASI"] = "GPS"
    # Radius ketidakpastian GPS perangkat (m). Opsional: klien lama / antrean luring tidak ditolak (K-12).
    accuracy_m: float | None = Field(None, ge=0)
    # Foto bukti: hanya diwajibkan di luar radius (trigger DB).
    selfie_file_id: UUID | None = None
    # Pengenalan wajah: id gambar wajah sementara dari POST /face/probe. Hasil dihitung SERVER (aturan inti #3).
    face_probe_id: UUID | None = None
    # DEPRECATED & DIABAIKAN: klien tidak lagi dipercaya soal hasil wajah. Dipertahankan agar APK lama tidak ditolak.
    face_result: Literal["MATCH", "NO_MATCH", "LOW_QUALITY", "NOT_ENROLLED", "SKIPPED"] | None = None
    face_similarity: float | None = None
    # R-33: Wajib diisi bila berada di luar radius lokasi atau saat mengajukan ulang absensi yang ditolak.
    explanation: str | None = Field(None, max_length=1000)


class CheckOutRequest(BaseModel):
    """
    Schema for processing a check-out request.
    """
    channel: AttendanceChannel = "MOBILE"
    location: GeoPoint
    location_origin: Literal["GPS", "SIMULASI"] = "GPS"
    # Pengenalan wajah saat pulang (tanpa foto bukti): id gambar wajah sementara dari POST /face/probe.
    face_probe_id: UUID | None = None


class ExplanationRequest(BaseModel):
    """
    Schema for supplying an explanation to an attendance record.
    """
    explanation: str


class ReviewRequest(BaseModel):
    """
    Schema for reviewing (approving or rejecting) an attendance event.
    """
    is_approved: bool
    note: str | None = None


class AttendanceResponse(BaseModel):
    """
    Schema detailing a single day's attendance record for an employee.
    """
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
    # Pengenalan wajah hasil hitung server (MATCH/NO_MATCH/LOW_QUALITY/NOT_ENROLLED/SKIPPED); None = tidak diperiksa.
    face_result: str | None = None
    face_similarity: float | None = None
    check_out_face_result: str | None = None
    check_out_face_similarity: float | None = None
    # Hanya terisi di daftar GET /attendance
    # Alasan peninjau bila absensi ditolak
    review_note: str | None = None
    employee_name: str | None = None
    # Peminta berwenang meninjau baris ini (R-33, dihitung oleh server)
    can_review: bool = False
    # R-34: Absen luring — catatan pemeriksaan server & jam pulang yang menunggu persetujuan absen masuk.
    offline: bool = False
    offline_note: str | None = None
    check_out_requested_at: datetime | None = None


class AttendanceListResponse(BaseModel):
    """
    Schema for paginated responses of attendance records.
    """
    items: list[AttendanceResponse]
    total: int
    page: int
    size: int
    # O-10: Tanggal hari ini menurut zona waktu organisasi. 
    # Aplikasi HP menandai "absensi hari ini" menggunakan nilai ini, bukan jam perangkat.
    today: date | None = None
    # R-34: Jangkar waktu bertanda tangan server untuk absen luring.
    # Mewakili jam server saat ini, berlaku selama 30 hari.
    time_anchor: str | None = None


class DeviceKeyRequest(BaseModel):
    """
    Schema for registering a device public key.
    Kunci publik EC P-256 (X.509 SubjectPublicKeyInfo DER, base64) dari Android Keystore.
    """
    device_id: str = Field(..., min_length=8, max_length=100)
    public_key: str = Field(..., min_length=40, max_length=1000)


class OfflineAttendanceEvent(BaseModel):
    """
    Schema representing a signed offline attendance event.
    Satu absen luring: `payload` adalah JSON persis seperti yang ditandatangani oleh HP;
    `signature` adalah tanda tangan ECDSA SHA-256 (DER, base64).
    Swafoto diunggah lebih dulu; kecocokannya dicek melalui `selfie_sha256` dalam payload.
    """
    device_id: str = Field(..., min_length=8, max_length=100)
    client_op_id: UUID
    kind: Literal["CHECK_IN", "CHECK_OUT"]
    payload: str = Field(..., max_length=10000)
    signature: str = Field(..., max_length=500)
    selfie_file_id: UUID | None = None
    # Gambar wajah sementara (POST /face/probe); kecocokannya dicek lewat `face.probe_sha256` dalam payload.
    face_probe_id: UUID | None = None


class OfflineAttendanceResult(BaseModel):
    """
    Schema detailing the result of processing an offline attendance event.
    """
    client_op_id: UUID
    # Status absen masuk (AUTO_VALID/NEEDS_REVIEW) atau CHECKED_OUT / CHECK_OUT_PENDING_REVIEW
    result: str
    attendance_id: UUID | None
    duplicate: bool
    event_time: datetime | None = None
    time_trusted: bool | None = None
    notes: list[str] = []


class MissingCheckInResponse(BaseModel):
    """
    Schema for missing check-in alerts (moved from attendance cron endpoint).
    """
    alerted: bool
    check_ins_today: int


class NeedsReviewResponse(BaseModel):
    """
    Schema for review alerts.
    """
    alerted: bool
    needs_review_today: int
    daily_average: float
