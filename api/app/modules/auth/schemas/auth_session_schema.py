"""
app/modules/auth/schemas/auth_session_schema.py

Skema sesi perangkat aktif dan pencabutan sesi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.5.
"""
from datetime import datetime

from pydantic import BaseModel


class AuthSessionResponseSchema(BaseModel):
    """
    Skema detail satu sesi perangkat aktif.
    """
    id: str
    device_label: str | None
    ip_address: str | None
    user_agent: str | None
    issued_at: datetime | None
    last_used_at: datetime | None
    current: bool


class AuthRevokeOthersResponseSchema(BaseModel):
    """
    Skema respons setelah mencabut semua sesi perangkat lain.
    """
    revoked: int
    message: str


# Alias untuk kompatibilitas
SessionOut = AuthSessionResponseSchema
RevokeOthersResponse = AuthRevokeOthersResponseSchema

