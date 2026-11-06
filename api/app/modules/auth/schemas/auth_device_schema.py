"""
app/modules/auth/schemas/auth_device_schema.py

Kontrak kredensial perangkat (masuk dengan sidik jari). Token perangkat hanya muncul di respons penerbitan
dan respons masuk; basis data hanya menyimpan SHA-256-nya.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.auth.schemas.auth_login_response_schema import AuthLoginResponseSchema

DEVICE_TOKEN_MAX = 128  # token asli 43 karakter; batas ini juga dipakai mobile


class DeviceCredentialResponseSchema(BaseModel):
    """Token perangkat baru. Simpan di penyimpanan aman HP; tidak bisa dilihat lagi."""

    device_token: str
    expires_at: datetime
    device_label: str


class BiometricLoginRequestSchema(BaseModel):
    device_token: str = Field(min_length=20, max_length=DEVICE_TOKEN_MAX)


class BiometricLoginResponseSchema(AuthLoginResponseSchema):
    """Sama seperti login biasa, ditambah token perangkat pengganti (token lama sudah tidak berlaku)."""

    device_token: str
    device_token_expires_at: datetime
