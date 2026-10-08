"""Skema permintaan & respons terkait Rencana Kerja (Work Plan)."""
from datetime import date
from uuid import UUID

from pydantic import BaseModel


class WorkPlanBase(BaseModel):
    """Skema dasar untuk Rencana Kerja.

    Menyimpan atribut-atribut umum dari sebuah Work Plan seperti
    judul, unit penanggung jawab, lokasi, periode, dan peran utama.
    """
    title: str  # Judul rencana kerja
    unit_id: UUID  # ID unit penanggung jawab
    site_id: UUID | None = None  # ID situs lokasi kerja (opsional)
    location_text: str  # Nama atau deksripsi lokasi dalam bentuk teks
    description: str | None = None  # Deskripsi rencana kerja
    period_start: date  # Tanggal mulai pelaksanaan
    period_end: date  # Tanggal akhir pelaksanaan
    pm_employee_id: UUID  # ID pegawai Project Manager (PM)
    leader_employee_id: UUID | None = None  # ID pegawai ketua tim di lapangan (opsional)

class WorkPlanCreate(WorkPlanBase):
    """Skema untuk membuat Rencana Kerja baru."""

class WorkPlanUpdate(BaseModel):
    """Skema untuk memperbarui data Rencana Kerja."""
    title: str | None = None  # Judul rencana kerja
    site_id: UUID | None = None  # ID situs lokasi kerja
    location_text: str | None = None  # Teks lokasi
    description: str | None = None  # Deskripsi rencana kerja
    period_start: date | None = None  # Tanggal mulai
    period_end: date | None = None  # Tanggal berakhir
    leader_employee_id: UUID | None = None  # ID pegawai ketua tim
    row_version: int  # Versi baris untuk kontrol konkurensi (optimistic locking)

class WorkPlanResponse(WorkPlanBase):
    """Skema respons untuk Rencana Kerja.

    Menyertakan status, nomor dokumen, revisi, dan alasan penolakan jika ada.
    """
    id: UUID  # ID rencana kerja
    number: str | None = None  # Nomor dokumen (opsional)
    status: str  # Status dari rencana kerja (misal: DRAFT, APPROVED, dll)
    revision: int  # Nomor revisi dari rencana kerja
    row_version: int  # Versi baris untuk manajemen konflik
    cancellation_reason: str | None = None  # Alasan pembatalan (jika dibatalkan)
    appeal_reason: str | None = None  # Alasan banding (jika ada sanggahan penolakan)
    category: str | None = None   # alur SK v2 - Kategori pekerjaan
    is_out_of_town: bool = False  # Rencana kerja luar kota
    pending_request: bool = False  # T2: ada permintaan revisi dari ketua yang menunggu PM


class AssignmentEmployeeOption(BaseModel):
    """Skema opsi pegawai untuk penugasan."""
    id: UUID  # ID pegawai
    full_name: str  # Nama lengkap pegawai
    position: str  # Jabatan pegawai
    unit_id: UUID | None = None  # ID unit asal pegawai


class PlanAssignmentOptions(BaseModel):
    """Skema opsi penugasan pada Rencana Kerja.

    Mengelompokkan opsi pegawai yang tersedia untuk menjadi PM atau personel lapangan.
    """
    can_choose_pm: bool  # Apakah diperbolehkan memilih PM secara bebas
    fixed_pm_employee_id: UUID | None = None  # ID PM yang sudah ditetapkan secara pasti (opsional)
    fixed_unit_id: UUID | None = None  # ID unit penugasan yang tetap (opsional)
    pm_options: list[AssignmentEmployeeOption]  # Daftar pegawai yang bisa dipilih menjadi PM
    personnel_options: list[AssignmentEmployeeOption]  # Daftar pegawai yang bisa dipilih sebagai anggota tim

class PlanMemberListResponse(BaseModel):
    """Skema respons untuk daftar anggota Rencana Kerja."""
    id: UUID  # ID keanggotaan
    employee_id: UUID  # ID pegawai yang menjadi anggota
    role_in_plan: str  # Peran pegawai dalam rencana kerja (misal: LEADER, MEMBER)
    valid_from: date  # Tanggal mulai efektif bergabung
    valid_to: date  # Tanggal akhir efektif bergabung

class PlanDayCreate(BaseModel):
    """Skema pembuatan aktivitas harian dalam Rencana Kerja."""
    work_date: date  # Tanggal pengerjaan aktivitas
    title: str  # Judul atau nama ringkas dari hari kerja tersebut
    sort_order: int = 0  # Urutan tampilan aktivitas

class PlanTaskCreate(BaseModel):
    """Skema pembuatan tugas spesifik dalam suatu aktivitas harian."""
    title: str  # Judul atau deskripsi singkat tugas
    sort_order: int = 0  # Urutan eksekusi/tampilan tugas

class PlanDayResponse(PlanDayCreate):
    """Skema respons aktivitas harian dalam Rencana Kerja."""
    id: UUID  # ID dari entitas hari kerja
    work_plan_id: UUID  # ID rencana kerja yang berelasi

class PlanTaskResponse(PlanTaskCreate):
    """Skema respons untuk tugas spesifik pada aktivitas harian."""
    id: UUID  # ID tugas
    work_plan_day_id: UUID  # ID hari kerja yang berelasi
    is_done: bool  # Menandakan apakah tugas telah selesai dikerjakan


# ── Dipindah dari api/v1/endpoints/work_plans.py (R-28 M2b) ──
class DayTaskInput(BaseModel):
    """Input tugas harian dari pengguna."""
    title: str  # Judul tugas


class DayPlanRequest(BaseModel):
    """Permintaan pembuatan atau pembaruan rencana harian beserta tugas-tugasnya."""
    title: str  # Judul kegiatan harian
    tasks: list[DayTaskInput]  # Daftar tugas yang akan dilakukan
