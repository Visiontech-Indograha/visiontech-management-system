"""
Modul utama (main) untuk aplikasi VMS FastAPI.

Modul ini bertanggung jawab untuk inisialisasi aplikasi, middleware,
logging terstruktur, serta rute-rute dasar (health, ready) dan router utama.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.logging_config import RequestIDMiddleware, setup_logging
from app.core.version import APP_VERSION
from app.database.health_check import check_database_health

setup_logging()
logger = logging.getLogger(__name__)

# Basis semua rute aplikasi (dok 05). /health dan /ready tetap di akar untuk Caddy & pemantauan.
API_PREFIX = "/api/v1"

def create_app() -> FastAPI:
    """
    Fungsi pembuat instance FastAPI utama (factory method).
    Mendaftarkan middleware, error handler, lifespan, dan router rute (endpoints).
    """
    app = FastAPI(title=settings.PROJECT_NAME, version=APP_VERSION, lifespan=lifespan)

    # Daftarkan middleware CORS
    # Wildcard + credentials membuat situs mana pun bisa memakai cookie refresh pengguna; credentials hanya
    # untuk origin yang didaftarkan. Web produksi satu origin dengan API (proxy), jadi tidak butuh CORS.
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=bool(origins),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count"],
    )

    # Daftarkan middleware RequestID
    app.add_middleware(RequestIDMiddleware)

    # Daftarkan penanganan galat aplikasi (error handlers)
    register_exception_handlers(app)

    # Mount direktori uploads fisik untuk akses foto & dokumen
    uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Endpoint pemeriksaan kesehatan sederhana (liveness probe)."""
        return {"status": "ok", "version": APP_VERSION}

    @app.get(f"{API_PREFIX}/version")
    async def version_info() -> dict[str, str]:
        """Versi API (SemVer) — sama dengan berkas VERSION di root repo."""
        return {"version": APP_VERSION}

    @app.get("/ready")
    async def readiness_check() -> JSONResponse:
        """
        Endpoint kesiapan (readiness probe).
        Memastikan basis data benar-benar bisa dihubungi sebelum melayani request.
        """
        is_healthy = await check_database_health()
        if not is_healthy:
            return JSONResponse(
                {"status": "not_ready", "db": "unreachable", "version": APP_VERSION}, status_code=503
            )
        return JSONResponse({"status": "ready", "db": "ok", "version": APP_VERSION})

    # Memasukkan router utama v1 ke dalam aplikasi
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix=API_PREFIX)

    return app

# Instance aplikasi FastAPI utama yang siap dijalankan oleh server (seperti Uvicorn)
app = create_app()
