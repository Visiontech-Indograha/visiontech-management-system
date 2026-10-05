"""Skema permintaan & respons: plan day (dipindah dari api/v1/endpoints/work_plan_days.py, R-28 M2b)."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


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
