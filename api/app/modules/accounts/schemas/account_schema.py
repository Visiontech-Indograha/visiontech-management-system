"""
app/schemas/account.py

Request and response schemas for user accounts.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Peran lapangan yang boleh dipilih HR/SUPER_ADMIN lewat akun karyawan (selain ini: peran kantor/admin ditolak).
FieldRole = Literal["EMPLOYEE", "TEAM_LEADER"]


class AccountOut(BaseModel):
    """
    Schema for account output data, detailing user authentication and status.
    """
    exists: bool
    user_id: UUID | None = None
    login: str | None = None
    is_active: bool | None = None
    last_login_at: datetime | None = None
    # Kegagalan login dalam 15 menit terakhir; `locked_until` terisi bila akun sedang terkunci.
    failed_logins: int = 0
    locked_until: datetime | None = None
    # Peran sistem akun (system_role); None bila belum ada akun.
    system_role: str | None = None


class AccountCreate(BaseModel):
    """
    Schema for creating a new user account.
    """
    # Kolom login dibatasi menggunakan pola regex untuk format email
    login: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    # Peran lapangan; default karyawan biasa. Hanya HR/SUPER_ADMIN yang boleh memilih TEAM_LEADER.
    system_role: FieldRole = "EMPLOYEE"


class AccountRoleUpdate(BaseModel):
    """Ubah peran lapangan akun karyawan (EMPLOYEE ↔ TEAM_LEADER)."""
    system_role: FieldRole


class AccountLoginUpdate(BaseModel):
    """Ubah email login akun (dipakai untuk masuk; unik di seluruh sistem)."""
    login: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)


class AccountSessionsRevoked(BaseModel):
    """Jumlah sesi perangkat yang dicabut oleh HR/admin."""
    revoked: int


class AccountWithPassword(AccountOut):
    """
    Schema for account creation response, including the generated temporary password.
    """
    # Sandi sementara yang harus segera diubah
    temporary_password: str
