"""
app/modules/auth/schemas/auth_login_request_schema.py

Skema data permintaan login pengguna.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.5.
"""

from pydantic import BaseModel, Field


class AuthLoginRequestSchema(BaseModel):
    """
    Skema payload untuk permintaan login akun.
    """

    email: str = Field(max_length=254)
    password: str = Field(max_length=256)
    platform: str | None = Field(default="web", max_length=20)


# Alias untuk kompatibilitas
LoginRequest = AuthLoginRequestSchema
