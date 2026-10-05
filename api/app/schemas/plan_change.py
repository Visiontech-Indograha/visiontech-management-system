"""Skema permintaan & respons: plan change (dipindah dari api/v1/endpoints/work_plan_changes.py, R-28 M2b)."""
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChangeRequest(BaseModel):
    """Permintaan perubahan (Change Request) pada Rencana Kerja.
    
    Menangani perubahan jenis ekstensi waktu (EXTEND) atau penyesuaian personel lapangan (PERSONNEL).
    """
    type: Literal["EXTEND", "PERSONNEL"]  # Tipe perubahan: perpanjangan waktu atau pengubahan personel
    reason: str = ""  # Alasan diajukannya perubahan
    new_period_end: date | None = None                        # EXTEND - Tanggal baru batas akhir pekerjaan
    leader_employee_id: UUID | None = None                    # PERSONNEL - ID ketua tim (leader) yang baru
    member_employee_ids: list[UUID] = Field(default_factory=list)  # PERSONNEL - Daftar ID anggota yang baru


class DecisionRequest(BaseModel):
    """Permintaan keputusan persetujuan atau penolakan atas pengajuan perubahan."""
    reason: str | None = None  # Alasan keputusan yang diberikan (catatan penolakan/persetujuan)


class ChangeResponse(BaseModel):
    """Respons detail dari sebuah entri perubahan Rencana Kerja."""
    id: UUID  # ID perubahan
    work_plan_id: UUID  # ID Rencana Kerja terkait
    change_type: str  # Tipe dari perubahan (misal EXTEND atau PERSONNEL)
    status: str  # Status dari permohonan perubahan (PENDING, APPROVED, REJECTED)
    reason: str  # Alasan diajukannya perubahan dari pengguna
    decision_reason: str | None = None  # Catatan/alasan keputusan yang diberikan oleh pemberi izin

