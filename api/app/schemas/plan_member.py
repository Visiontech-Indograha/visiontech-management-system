"""Skema permintaan & respons: plan member (dipindah dari api/v1/endpoints/work_plan_members.py, R-28 M2b)."""
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class TeamMemberOut(BaseModel):
    """Respons detail dari anggota tim dalam suatu Rencana Kerja."""
    employee_id: str  # ID pegawai anggota
    full_name: str  # Nama lengkap anggota
    position: str | None  # Jabatan dari anggota tim
    role_in_plan: str  # Peran di dalam rencana kerja (contoh: LEADER atau MEMBER)
    valid_from: date | None  # Tanggal anggota mulai berlaku masuk ke tim


class TeamRequest(BaseModel):
    """Permintaan pembaruan/penyesuaian tim di dalam Rencana Kerja."""
    leader_employee_id: UUID | None = None  # ID pegawai yang ditunjuk sebagai ketua
    member_employee_ids: list[UUID] = Field(default_factory=list)  # Daftar ID pegawai yang ditunjuk sebagai anggota
    row_version: int  # Versi baris (optimistic locking) dari Rencana Kerja saat ini


class TeamResponse(BaseModel):
    """Respons setelah pembaruan susunan tim Rencana Kerja dilakukan."""
    leader_employee_id: str | None  # ID pegawai ketua tim
    member_employee_ids: list[str]  # Daftar ID pegawai anggota tim
    row_version: int  # Versi baris terbaru dari Rencana Kerja
