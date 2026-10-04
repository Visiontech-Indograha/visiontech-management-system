"""
app/schemas/account.py

Request and response schemas for user accounts.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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


class AccountCreate(BaseModel):
    """
    Schema for creating a new user account.
    """
    # Kolom login dibatasi menggunakan pola regex untuk format email
    login: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)


class AccountWithPassword(AccountOut):
    """
    Schema for account creation response, including the generated temporary password.
    """
    # Sandi sementara yang harus segera diubah
    temporary_password: str
