from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str
    platform: str | None = "web"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    role: str
    permissions: list[str]
    employee_id: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


class SessionOut(BaseModel):
    """Satu perangkat yang sedang masuk (P1-7). `current` = perangkat yang sedang dipakai."""
    id: str
    device_label: str | None
    ip_address: str | None
    user_agent: str | None
    issued_at: datetime | None
    last_used_at: datetime | None
    current: bool


class RevokeOthersResponse(BaseModel):
    revoked: int
    message: str

