"""
Modul utama (main) untuk aplikasi VMS FastAPI.

Modul ini bertanggung jawab untuk inisialisasi aplikasi, middleware,
logging terstruktur, serta rute-rute dasar (health, ready) dan router utama.
"""
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers


class JSONFormatter(logging.Formatter):
    """
    Formatter kustom untuk mencetak log dalam format JSON.
    Berguna untuk integrasi dengan sistem manajemen log (seperti ELK, Datadog).
    """
    def format(self, record: logging.LogRecord) -> str:
        """Membentuk satu catatan log menjadi string JSON."""
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": request_id_context.get(None),
        }
        return json.dumps(log_record)

# Konteks untuk menyimpan request ID secara asinkron (per request)
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

def setup_logging() -> None:
    """
    Mengatur konfigurasi logging dasar aplikasi untuk menggunakan format JSON.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)

setup_logging()
logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware untuk menyisipkan request ID yang unik di setiap siklus HTTP request/response.
    Berguna untuk penelusuran (tracing) log per request.
    """
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Memproses request, menetapkan request ID, dan mengembalikan response."""
        # Ambil request ID dari header jika ada, atau buat UUID baru
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_context.set(req_id)
        response = await call_next(request)
        # Tambahkan kembali request ID ke header response
        response.headers["X-Request-ID"] = req_id
        return response

# Basis semua rute aplikasi (dok 05). /health dan /ready tetap di akar untuk Caddy & pemantauan.
API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """
    Fungsi pembuat instance FastAPI utama (factory method).
    Mendaftarkan middleware, error handler, dan router rute (endpoints).
    """
    app = FastAPI(title=settings.PROJECT_NAME)
    
    # Daftarkan middleware
    app.add_middleware(RequestIDMiddleware)
    
    # Daftarkan penanganan galat aplikasi (error handlers)
    register_error_handlers(app)  # bentuk galat baku dok 05 §2 (app/core/errors.py)


    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Endpoint pemeriksaan kesehatan sederhana (liveness probe)."""
        return {"status": "ok"}
        
    @app.get("/ready")
    async def readiness_check() -> JSONResponse:
        """
        Endpoint kesiapan (readiness probe). 
        Memastikan basis data benar-benar bisa dihubungi sebelum melayani request.
        """
        # Siap = basis data benar-benar menjawab; dipakai autodeploy sebelum lapor "berhasil".
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError

        from app.db.session import engine

        try:
            # Mencoba koneksi ke database dan memverifikasi keberadaan skema
            async with engine.connect() as conn:
                schema_ok = await conn.scalar(text("SELECT to_regclass('vms.organization') IS NOT NULL"))
        except (OSError, SQLAlchemyError):
            schema_ok = None
            
        if not schema_ok:
            return JSONResponse({"status": "not_ready", "db": "unreachable"}, status_code=503)
        return JSONResponse({"status": "ready", "db": "ok"})
        
    # Memasukkan router utama v1 ke dalam aplikasi
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix=API_PREFIX)
        
    return app

# Instance aplikasi FastAPI utama yang siap dijalankan oleh server (seperti Uvicorn)
app = create_app()
