"""
app/modules/auth/schemas/auth_profile_schema.py

Skema profil pengguna yang sedang masuk dan perubahan kata sandi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.5.
"""

from pydantic import BaseModel, Field


class ManagedDivisionOut(BaseModel):
    """Ringkasan divisi yang dikelola atau dinaungi pengguna."""
    division_id: str
    name: str
    is_pm: bool = False
    is_om: bool = False


class AuthUserMeResponseSchema(BaseModel):
    """
    Skema detail identitas pengguna yang sedang terautentikasi (/me).
    """

    user_id: str
    email: str
    role: str
    permissions: list[str]
    employee_id: str | None = None
    attendance_mode: str | None = None
    division_id: str | None = None
    managed_division_ids: list[str] = Field(default_factory=list)
    managed_divisions: list[ManagedDivisionOut] = Field(default_factory=list)
    photo_file_id: str | None = None
    full_name: str | None = None


class AuthChangePasswordRequestSchema(BaseModel):
    """
    Skema permohonan ganti kata sandi.
    """

    current_password: str = Field(max_length=256)
    new_password: str = Field(max_length=128)


class AuthMessageResponseSchema(BaseModel):
    """
    Skema respons pesan status operasional umum.
    """

    message: str


# Alias untuk kompatibilitas
UserMeResponse = AuthUserMeResponseSchema
ChangePasswordRequest = AuthChangePasswordRequestSchema
MessageResponse = AuthMessageResponseSchema
