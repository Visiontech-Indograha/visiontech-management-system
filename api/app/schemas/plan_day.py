"""Skema permintaan & respons: plan day (dipindah dari api/v1/endpoints/work_plan_days.py, R-28 M2b)."""
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.work_type import EvidenceOut


class DayTaskOut(BaseModel):
    """Skema respons untuk tugas harian."""
    id: UUID  # ID tugas
    title: str  # Judul tugas harian
    sort_order: int  # Urutan tampilan tugas
    is_done: bool  # Status penyelesaian tugas (selesai atau belum)
    done_at: datetime | None  # Waktu saat tugas diselesaikan


class DayReportOut(BaseModel):
    """Skema respons untuk laporan harian."""
    status: str  # Status dari laporan (misal: SUBMITTED, APPROVED)
    body: str  # Isi laporan yang dikirimkan
    obstacle: str  # Rintangan atau kendala yang dihadapi
    review_note: str | None  # Catatan evaluasi dari reviewer (jika ada)
    submitted_at: datetime | None  # Waktu pengiriman laporan
    reviewed_at: datetime | None  # Waktu saat laporan ditelaah/direview
    evidence_file_ids: list[UUID]  # Daftar ID file lampiran bukti penyelesaian
    evidence: list[EvidenceOut] = []  # Bukti berlabel slot template + sumber (T9)
    resubmitted: bool = False   # "Dikirim ulang" (alur SK v2) - Indikator laporan dikirim ulang


class PlanDayOut(BaseModel):
    """Skema respons keseluruhan untuk rencana hari kerja."""
    id: UUID  # ID aktivitas hari kerja
    work_date: date  # Tanggal hari kerja terkait
    title: str  # Judul kegiatan di hari tersebut
    sort_order: int  # Urutan tampilan hari
    tasks: list[DayTaskOut]  # Daftar tugas yang direncanakan pada hari tersebut
    report: DayReportOut | None  # Detail laporan harian jika sudah diisi
    member_reports_sent: int = 0  # Jumlah laporan yang dikirim oleh anggota tim pada hari ini
    site_name: str | None = None  # Lokasi khusus hari itu (None = ikut lokasi rencana)
    work_type_name: str | None = None  # Jenis pekerjaan khusus hari itu (None = ikut jenis rencana)
    member_employee_ids: list[UUID] | None = None  # Yang bertugas hari itu, termasuk ketua (None = seluruh tim)


class SopImageRequirementOut(BaseModel):
    """Skema persyaratan foto SOP untuk tipe pekerjaan."""
    title: str
    description: str | None = None
    path_image: str | None = None


class WorkTypeWithSopOut(BaseModel):
    """Skema tipe pekerjaan lengkap beserta persyaratan foto SOP."""
    work_type_id: UUID
    name: str
    description: str | None = None
    sop_image_requirements: list[SopImageRequirementOut] = []


class WorkCompletionOrderSummaryOut(BaseModel):
    """Ringkasan order klien (work completion) yang terhubung ke slot penugasan."""
    completion_id: UUID
    order_number: str
    client_name: str
    project_title: str
    total_target_unit: float | None = None
    unit_measure: str | None = None
    order_status: str
    priority_level: str | None = None


class ItemScheduleSlotOut(BaseModel):
    """Slot jadwal item tugas spesifik di hari kerja."""
    item_id: UUID
    start_time: str | None = None
    end_time: str | None = None
    title: str
    location_name: str | None = None
    site_lat: float | None = None
    site_lng: float | None = None
    target_qty: float = 0.0
    completed_qty: float = 0.0
    progress_percent: float = 0.0
    status: str
    assigned_employee_ids: list[Any] = []
    work_type: WorkTypeWithSopOut | None = None
    work_completion_order: WorkCompletionOrderSummaryOut | None = None


class WeeklyContextDivisionOut(BaseModel):
    """Konteks divisi untuk jadwal mingguan."""
    division_id: UUID
    name: str


class WeeklyContextTeamOut(BaseModel):
    """Konteks tim pelaksana untuk jadwal mingguan."""
    team_id: UUID
    name: str


class WeeklyContextOut(BaseModel):
    """Konteks jadwal mingguan induk."""
    weekly_plan_id: UUID
    week_number: int
    year: int
    division: WeeklyContextDivisionOut
    team: WeeklyContextTeamOut


class DefaultAttendanceSiteOut(BaseModel):
    """Informasi lokasi absensi induk harian."""
    site_name: str | None = None
    site_lat: float | None = None
    site_lng: float | None = None
    attendance_radius_m: int | None = None
    clock_in_time: str | None = None
    clock_out_time: str | None = None


class PlanDailyScheduleDetailOut(BaseModel):
    """Respons detail rencana kerja harian lengkap multi-slot untuk web & mobile."""
    daily_plan_id: UUID
    work_date: date
    status: str
    can_pm_edit: bool = True
    preview_pdf_url: str | None = None
    weekly_context: WeeklyContextOut
    default_attendance_site: DefaultAttendanceSiteOut
    items_schedule_slots: list[ItemScheduleSlotOut] = []

