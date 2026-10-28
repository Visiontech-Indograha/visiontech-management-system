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
    # Radius ketidakpastian GPS perangkat (m). Opsional: klien lama / antrean offline tidak ditolak (K-12).
    accuracy_m: float | None = Field(None, ge=0)
    # Swafoto absen (wajib): dicocokkan server dengan wajah terdaftar (M7); juga foto bukti di luar radius.
    selfie_file_id: UUID | None = None
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
    # T7: di luar radius lokasi, swafoto + penjelasan wajib (jarak dihitung ulang oleh server).
    selfie_file_id: UUID | None = None
    explanation: str | None = Field(None, max_length=1000)
    accuracy_m: float | None = Field(None, ge=0)


class ExplanationRequest(BaseModel):
    """
    Schema for supplying an explanation to an attendance record.
    """
    explanation: str


class AttendanceAdminPatch(BaseModel):
    """Koreksi absensi oleh SUPER_ADMIN; hanya kolom yang dikirim yang diubah. `reason` masuk ke audit."""
    clock_in_at: datetime | None = None
    clock_out_at: datetime | None = None
    om_approval_status: Literal["AUTO_VALID", "PENDING_OM", "APPROVED_BY_OM", "REJECTED_BY_OM"] | None = None
    out_of_radius_note: str | None = None
    reason: str = Field(min_length=3, max_length=500)


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
    employee_photo_file_id: UUID | None = None
    # Peminta berwenang meninjau baris ini (R-33, dihitung oleh server)
    can_review: bool = False
    # R-34: Absen offline — catatan pemeriksaan server & jam pulang yang menunggu persetujuan absen masuk.
    offline: bool = False
    offline_note: str | None = None
    check_out_requested_at: datetime | None = None
    # T7: absen pulang di luar radius + kategori dalam/luar kota (dihitung saat dibaca).
    check_out_distance_m: float | None = None
    check_out_outside: bool = False
    check_out_selfie_file_id: UUID | None = None
    check_out_explanation: str | None = None
    city_category: str | None = None
    meal_allowance_amount: float | None = None
    is_within_attendance_radius: bool | None = None
    # Pesan penyemangat saat karyawan menyelesaikan waktu kerja penuh (8 jam kerja efektif)
    encouragement_message: str | None = None


class MealAllowanceRow(BaseModel):
    """Rekap uang makan per karyawan (docs/35 §5): hanya absensi sah (AUTO_VALID / APPROVED_BY_OM)."""
    employee_id: UUID
    employee_no: str | None = None
    full_name: str
    in_city_days: int
    out_city_days: int
    total_amount: float
    pending_days: int  # absensi yang masih menunggu OM — belum dibayar


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
    # Jam wajib pulang sesi terbuka milik pemanggil (masuk+9 jam; terlambat = jam pulang kantor) → jadwal pengingat.
    required_out_at: datetime | None = None
    # Jumlah tugas hari ini yang progresnya belum diperbarui (peringatan laporan harian; tidak memblokir absen).
    report_pending_count: int = 0
    report_pending_plan_id: UUID | None = None
    # R-34: Jangkar waktu bertanda tangan server untuk absen offline.
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
    Satu absen offline: `payload` adalah JSON persis seperti yang ditandatangani oleh HP;
    `signature` adalah tanda tangan ECDSA SHA-256 (DER, base64).
    Swafoto diunggah lebih dulu; kecocokannya dicek melalui `selfie_sha256` dalam payload.
    """
    device_id: str = Field(..., min_length=8, max_length=100)
    client_op_id: UUID
    kind: Literal["CHECK_IN", "CHECK_OUT"]
    payload: str = Field(..., max_length=10000)
    signature: str = Field(..., max_length=500)
    selfie_file_id: UUID | None = None


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


class MyRecapItem(BaseModel):
    work_date: date
    check_in_at: datetime
    check_out_at: datetime | None = None
    is_late: bool
    is_early_leave: bool
    is_valid: bool
    is_pending: bool
    meal_allowance_amount: float = 0
    city_zone: str | None = None


class MyRecapResponse(BaseModel):
    """Rekap absensi bulanan milik sendiri (HP karyawan)."""
    month: str
    days_present: int
    late_days: int
    early_leave_days: int
    pending_days: int
    meal_allowance_total: float
    items: list[MyRecapItem]
