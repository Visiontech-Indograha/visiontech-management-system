from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Visiontech VMS"
    DATABASE_URL: str = "postgresql+asyncpg://vms_app:CHANGE_ME@100.117.92.14:5433/visiontech_db"
    JWT_SECRET_KEY: str = "supersecretkey_change_me_in_production"
    
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "vms-files"
    MINIO_SECURE: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
