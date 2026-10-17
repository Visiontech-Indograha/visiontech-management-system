"""
app/modules/accounts/schemas/account_schema.py

Skema kontrak request dan response untuk akun pengguna karyawan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.5.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AccountOut(BaseModel):
    """
    Skema data output akun, mendetailkan status autentikasi pengguna.
    """

    exists: bool
    user_id: UUID | None = None
    login: str | None = None
    is_active: bool | None = None
    last_login_at: datetime | None = None
    failed_logins: int = 0
    locked_until: datetime | None = None


class AccountCreate(BaseModel):
    """
    Skema data input untuk pembuatan akun karyawan baru.
    """

    login: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)


class AccountWithPassword(AccountOut):
    """
    Skema respons pembuatan/reset akun yang menyertakan kata sandi sementara.
    """

    temporary_password: str
