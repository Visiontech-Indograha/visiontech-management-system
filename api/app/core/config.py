from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Visiontech VMS"
    DATABASE_URL: str = "postgresql+asyncpg://vms_app:D3rJN0apzlCeOUcSyo4GEMzaJLTGYPs@100.117.92.14:5433/visiontech_db"
    
    class Config:
        env_file = ".env"

settings = Settings()
