"""Skema permintaan & respons: account (dipindah dari api/v1/endpoints/accounts.py, R-28 M2b)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AccountOut(BaseModel):
    exists: bool
    user_id: UUID | None = None
    login: str | None = None
    is_active: bool | None = None
    last_login_at: datetime | None = None
    failed_logins: int = 0
    """Kegagalan login dalam 15 menit terakhir; `locked_until` terisi bila akun sedang terkunci."""
    locked_until: datetime | None = None


class AccountCreate(BaseModel):
    login: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)


class AccountWithPassword(AccountOut):
    temporary_password: str
