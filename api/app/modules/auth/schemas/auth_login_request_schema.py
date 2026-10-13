"""
app/modules/auth/schemas/auth_login_request_schema.py

Skema data permintaan login pengguna.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.5.
"""
from pydantic import BaseModel


class AuthLoginRequestSchema(BaseModel):
    """
    Skema payload untuk permintaan login akun.
    """
    email: str
    password: str
    platform: str | None = "web"


# Alias untuk kompatibilitas
LoginRequest = AuthLoginRequestSchema

