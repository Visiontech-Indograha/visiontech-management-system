"""
app/modules/home/schemas/home_schema.py

Ringkasan Beranda: jumlah pekerjaan yang menunggu tindakan pengguna (sesuai peran) dan pengajuan miliknya.
"""

from pydantic import BaseModel, Field


class HomeSummary(BaseModel):
    """Semua angka 0 bila peran pengguna tidak berwenang meninjau; tidak pernah null."""

    leaves_to_review: int = Field(default=0, ge=0, description="Cuti menunggu keputusan pengguna")
    attendance_to_review: int = Field(default=0, ge=0, description="Absensi berstatus perlu review")
    overtime_to_review: int = Field(default=0, ge=0, description="Lembur menunggu PM")
    mess_to_review: int = Field(default=0, ge=0, description="Pengajuan hunian mess menunggu")
    loan_requests_to_review: int = Field(default=0, ge=0, description="Pengajuan pinjam aset menunggu")
    corrections_to_review: int = Field(default=0, ge=0, description="Koreksi laporan harian menunggu tinjauan")
    offboarding_open: int = Field(default=0, ge=0, description="Proses offboarding yang belum selesai")
    my_leaves_pending: int = Field(default=0, ge=0, description="Cuti milik sendiri yang belum diputuskan")
    notifications_unread: int = Field(default=0, ge=0, description="Notifikasi belum dibaca")
    total_to_review: int = Field(default=0, ge=0, description="Jumlah semua yang menunggu tindakan pengguna")
