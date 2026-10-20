"""Skema form "Buat SK" alur v2 (flowchart SK2-A/B) dan notifikasi."""
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.work_types.schemas.work_type_schema import EvidenceIn, EvidenceOut

PlanCategory = Literal["INSTALASI", "PEMELIHARAAN", "PERBAIKAN", "SURVEI", "LAINNYA"]


class FormPerson(BaseModel):
    """Skema untuk menampilkan data orang/pegawai pada opsi formulir."""
    id: UUID  # ID pegawai
    full_name: str  # Nama lengkap pegawai
    position: str  # Jabatan pegawai
    busy_dates: list[date] = []  # Tanggal (hari ini dst.) ia sudah bertugas di rencana kerja aktif lain


class FormAsset(BaseModel):
    """Skema untuk menampilkan data aset (kendaraan atau alat) pada opsi formulir."""
    id: UUID  # ID aset
    kind: str  # Jenis aset (contoh: KENDARAAN, ALAT)
    vehicle_type: str | None = None  # Tipe spesifik untuk kendaraan (jika ada)
    code: str  # Kode inventaris aset
    name: str  # Nama aset


class FormSite(BaseModel):
    """Skema untuk menampilkan data lokasi/site pada opsi formulir."""
    id: UUID  # ID lokasi
    name: str  # Nama lokasi
    description: str | None = None  # Keterangan lokasi
    lat: float  # Titik lintang
    lng: float  # Titik bujur


class FormCategory(BaseModel):
    """Skema untuk menampilkan kategori Rencana Kerja pada opsi formulir."""
    code: str  # Kode kategori
    label: str  # Label kategori untuk tampilan UI


class PlanFormOptions(BaseModel):
    """Kumpulan opsi referensi (dropdown options) untuk formulir pembuatan SK (Rencana Kerja)."""
    unit_name: str | None  # Nama unit yang menaungi
    categories: list[FormCategory]  # Daftar kategori yang tersedia
    sites: list[FormSite]  # Daftar lokasi/site yang tersedia
    leaders: list[FormPerson]  # Daftar kandidat ketua tim
    members: list[FormPerson]  # Daftar kandidat anggota tim
    tools: list[FormAsset]  # Daftar opsi peralatan
    vehicles: list[FormAsset]  # Daftar opsi kendaraan


class NewSiteInput(BaseModel):
    """Masukan untuk membuat lokasi/site baru saat membuat Rencana Kerja."""
    name: str = Field(min_length=1, max_length=200)  # Nama situs lokasi baru
    description: str | None = Field(default=None, max_length=500)  # Deskripsi lokasi (opsional)
    lat: float = Field(ge=-90, le=90)  # Koordinat lintang lokasi
    lng: float = Field(ge=-180, le=180)  # Koordinat bujur lokasi


class DraftTaskInput(BaseModel):
    """Masukan tugas untuk draf Rencana Kerja."""
    title: str  # Judul tugas
    description: str  # Deskripsi rincian tugas
    file_ids: list[UUID] = []  # Daftar ID lampiran pendukung


class DraftDayInput(BaseModel):
    """Masukan aktivitas harian untuk draf Rencana Kerja."""
    work_date: date  # Tanggal aktivitas
    tasks: list[DraftTaskInput]  # Daftar tugas di hari tersebut
    site_id: UUID | None = None  # Lokasi khusus hari itu (kosong = ikut lokasi rencana)
    member_employee_ids: list[UUID] | None = None  # Anggota yang bertugas hari itu (kosong/None = seluruh tim)
    work_type_id: UUID | None = None  # Jenis pekerjaan khusus hari itu (kosong = ikut jenis rencana)


class PlanDraftRequest(BaseModel):
    """Permintaan pembuatan atau penyimpanan draf Rencana Kerja (SK v2)."""
    title: str  # Judul rencana kerja
    description: str  # Deskripsi rencana kerja
    category: PlanCategory  # Kategori rencana kerja
    site_id: UUID | None = None  # ID situs lokasi (jika sudah ada)
    new_site: NewSiteInput | None = None  # Data lokasi baru (jika belum ada)
    period_start: date  # Tanggal mulai
    period_end: date  # Tanggal berakhir
    days: list[DraftDayInput]  # Rincian aktivitas harian
    leader_employee_id: UUID  # ID pegawai yang ditunjuk sebagai ketua
    member_employee_ids: list[UUID] = []  # Daftar ID pegawai yang jadi anggota (opsional; ketua tetap wajib)
    is_out_of_town: bool = False  # Rencana kerja luar kota (uang absen luar kota)
    work_type_id: UUID | None = None  # Jenis pekerjaan (template foto laporan); opsional
    tool_ids: list[UUID] = []  # Daftar ID alat yang akan digunakan
    vehicle_id: UUID | None = None  # ID kendaraan operasional (opsional)
    driver_employee_id: UUID | None = None  # ID pegawai yang menjadi pengemudi (opsional)
    row_version: int | None = None   # wajib saat mengubah draf - versi baris Rencana Kerja


class PlanDetailOut(BaseModel):
    """Skema respons untuk melihat rincian komprehensif Rencana Kerja."""
    plan: dict[str, Any]  # Informasi umum Rencana Kerja
    team: list[dict[str, Any]]  # Susunan tim yang bertugas
    days: list[dict[str, Any]]  # Jadwal aktivitas harian
    assets: list[dict[str, Any]]  # Aset (alat & kendaraan) yang digunakan


class AmendmentRequest(BaseModel):
    """Permintaan perubahan/adendum pada draf yang sudah dibuat."""
    row_version: int  # Versi baris Rencana Kerja saat ini
    reason: str  # Alasan dilakukannya perubahan


class NotificationOut(BaseModel):
    """Skema respons untuk satu item notifikasi sistem."""
    id: UUID  # ID notifikasi
    kind: str  # Jenis notifikasi (INFO, WARNING, dsb.)
    title: str  # Judul pesan notifikasi
    body: str  # Isi pesan notifikasi
    work_plan_id: UUID | None = None  # ID rencana kerja yang terkait (opsional)
    created_at: datetime  # Waktu pembuatan notifikasi
    read_at: datetime | None = None  # Waktu notifikasi dibaca (jika sudah)


class NotificationList(BaseModel):
    """Daftar notifikasi untuk pengguna."""
    unread: int  # Jumlah notifikasi yang belum dibaca
    items: list[NotificationOut]  # Detail daftar notifikasi


# ── Laporan berjenjang (PR2) ─────────────────────────────────────────────────────────────────
class MemberReportIn(BaseModel):
    """Masukan laporan harian yang disusun oleh anggota tim."""
    body: str  # Isi laporan kinerja
    obstacle: str = ""  # Rintangan atau kendala (opsional)
    evidence_file_ids: list[UUID] = []  # Daftar ID file bukti pelaporan (APK lama)
    evidence: list[EvidenceIn] = []  # Foto bukti berlabel slot + sumber (T9)


class MemberReportOut(BaseModel):
    """Keluaran laporan dari anggota tim yang ditinjau."""
    id: UUID  # ID laporan
    employee_id: UUID  # ID pegawai pengirim
    full_name: str  # Nama lengkap pegawai
    position: str  # Jabatan pengirim
    status: str  # Status laporan (DRAFT, SUBMITTED, APPROVED, dsb)
    body: str  # Isi teks laporan
    obstacle: str  # Isi teks kendala
    sent_at: datetime | None = None  # Waktu laporan dikirim
    evidence_file_ids: list[UUID] = []  # Daftar file bukti
    evidence: list[EvidenceOut] = []  # Bukti berlabel slot + sumber (T9)


# ── Adendum saat berjalan (PR3) ──────────────────────────────────────────────────────────────
class AmendmentReasonIn(BaseModel):
    """Masukan berupa alasan diadakannya perubahan (adendum)."""
    reason: str  # Teks alasan


class PlanChangeOut(BaseModel):
    """Respons riwayat perubahan atau adendum suatu Rencana Kerja."""
    id: UUID  # ID riwayat perubahan
    change_type: str  # Jenis perubahan yang diajukan
    status: str  # Status dari pengajuan perubahan
    reason: str  # Alasan mengapa perubahan diajukan
    decision_reason: str | None = None  # Alasan dari pihak pengambil keputusan
    created_at: datetime  # Waktu permintaan diajukan
    requested_by_name: str | None = None  # Nama pihak yang mengajukan
    decided_by_name: str | None = None  # Nama pihak yang memutuskan
    document_id: UUID | None = None  # ID dokumen yang mendasari perubahan ini (jika ada)
