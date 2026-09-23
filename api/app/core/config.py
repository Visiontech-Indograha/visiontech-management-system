from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Visiontech VMS"
    # Nilai asli hanya di api/.env (tidak masuk Git). Bawaan ini sengaja tidak bisa login.
    DATABASE_URL: str = "postgresql+asyncpg://vms_app:CHANGE_ME@localhost:5433/visiontech_db"
    JWT_SECRET_KEY: str = "supersecretkey_change_me_in_production"
    
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
