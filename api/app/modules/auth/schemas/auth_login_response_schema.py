"""
app/modules/auth/schemas/auth_login_response_schema.py

Skema data keluaran token autentikasi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.5.
"""

from pydantic import BaseModel


class AuthLoginResponseSchema(BaseModel):
    """
    Skema respons token akses yang dikembalikan ke klien.
    """

    access_token: str
    token_type: str = "bearer"


# Alias untuk kompatibilitas
TokenResponse = AuthLoginResponseSchema
