"""
app/schemas/auth.py

Request and response schemas for authentication processes.
"""
from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """
    Schema for a user login request.
    """
    email: str
    password: str
    platform: str | None = "web"


class TokenResponse(BaseModel):
    """
    Schema for the returned authentication token.
    """
    access_token: str
    token_type: str = "bearer"


class UserMeResponse(BaseModel):
    """
    Schema for returning the authenticated user's details.
    """
    user_id: str
    email: str
    role: str
    permissions: list[str]
    employee_id: str | None = None
    # FIELD = absen lewat aplikasi HP, OFFICE = absen lewat web.
    # None = akun tanpa karyawan yang terkait.
    attendance_mode: str | None = None
    division_id: str | None = None


class ChangePasswordRequest(BaseModel):
    """
    Schema for a user requesting to change their password.
    """
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    """
    Schema for a simple status message response.
    """
    message: str


class SessionOut(BaseModel):
    """
    Schema representing a single active session/device (P1-7).
    `current` denotes the device currently being used.
    """
    id: str
    device_label: str | None
    ip_address: str | None
    user_agent: str | None
    issued_at: datetime | None
    last_used_at: datetime | None
    # Bernilai True bila ini adalah perangkat yang sedang melakukan permintaan
    current: bool


class RevokeOthersResponse(BaseModel):
    """
    Schema for the response after revoking other active sessions.
    """
    # Jumlah sesi lain yang berhasil dicabut
    revoked: int
    message: str
