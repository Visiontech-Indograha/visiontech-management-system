from pydantic_settings import BaseSettings


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
    
    # Discord #vms-alerts (dok 17). Kosong = peringatan hanya dicatat di log.
    DISCORD_WEBHOOK_ALERTS: str = ""

    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "[REDACTED-MINIO-USER]"
    MINIO_SECRET_KEY: str = "[REDACTED-MINIO-USER]"
    MINIO_BUCKET: str = "vms-files"
    MINIO_SECURE: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
