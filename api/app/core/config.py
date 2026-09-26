from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Visiontech VMS"
    # Nilai asli hanya di api/.env (tidak masuk Git). Bawaan ini sengaja tidak bisa login.
    DATABASE_URL: str = "postgresql+asyncpg://vms_app:CHANGE_ME@localhost:5433/visiontech_db"
    # Access token EdDSA (dok 08 §7): seed Ed25519 32 byte (hex). Nilai asli hanya di api/.env / KMS.
    JWT_PRIVATE_KEY_HEX: str = ""
    JWT_KID: str = "jwt-dev-1"
    # Tanda tangan dokumen (fase 6). Sementara: seed Ed25519 hex dari lingkungan; sebelum produksi diganti
    # adaptor KMS (keputusan pemilik 2026-09-26, dok 10). Kosong → kunci sementara per proses (dev/uji saja).
    DOC_SIGNING_KEY_HEX: str = ""
    DOC_SIGNING_KMS_REF: str = "env:DOC_SIGNING_KEY_HEX"
    PUBLIC_VERIFY_URL: str = "http://localhost:5173/verify"   # isi QR: <PUBLIC_VERIFY_URL>/<token>
    # Pencarian lokasi penugasan (revisi PM 2026-09-26): Nominatim/OpenStreetMap lewat backend.
    GEOCODER_URL: str = "https://nominatim.openstreetmap.org/search"
    GEOCODER_USER_AGENT: str = "VisiontechVMS/1.0 (lokasi-penugasan)"

    # Discord #vms-alerts (dok 17). Kosong = peringatan hanya dicatat di log.
    DISCORD_WEBHOOK_ALERTS: str = ""

    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "vms-files"
    MINIO_SECURE: bool = False
    
    # "production" menyalakan penjaga di bawah; nilai lain (development/test) memakai bawaan lokal.
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _production_requires_secrets(self) -> "Settings":
        """Produksi tidak boleh diam-diam memakai kunci JWT sementara, tanpa kunci tanda tangan,
        atau kredensial MinIO bawaan — API menolak start (dok 08)."""
        if self.APP_ENV.strip().lower() != "production":
            return self
        missing = [name for name, bad in (
            ("JWT_PRIVATE_KEY_HEX", not self.JWT_PRIVATE_KEY_HEX),
            ("DOC_SIGNING_KEY_HEX", self.DOC_SIGNING_KMS_REF.startswith("env:") and not self.DOC_SIGNING_KEY_HEX),
            ("MINIO_ACCESS_KEY", self.MINIO_ACCESS_KEY in ("", "minioadmin")),
            ("MINIO_SECRET_KEY", self.MINIO_SECRET_KEY in ("", "minioadmin")),
        ) if bad]
        if missing:
            raise ValueError("APP_ENV=production tetapi rahasia belum diisi / masih bawaan: " + ", ".join(missing))
        return self

settings = Settings()
