# Structured JSON logging
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
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": request_id_context.get(None),
        }
        return json.dumps(log_record)

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)

setup_logging()
logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_context.set(req_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

# Basis semua rute aplikasi (dok 05). /health dan /ready tetap di akar untuk Caddy & pemantauan.
API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)
    
    app.add_middleware(RequestIDMiddleware)
    
    register_error_handlers(app)  # bentuk galat baku dok 05 §2 (app/core/errors.py)


    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}
        
    @app.get("/ready")
    async def readiness_check() -> JSONResponse:
        # Siap = basis data benar-benar menjawab; dipakai autodeploy sebelum lapor "berhasil".
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError

        from app.core.database import engine

        try:
            async with engine.connect() as conn:
                schema_ok = await conn.scalar(text("SELECT to_regclass('vms.organization') IS NOT NULL"))
        except (OSError, SQLAlchemyError):
            schema_ok = None
        if not schema_ok:
            return JSONResponse({"status": "not_ready", "db": "unreachable"}, status_code=503)
        return JSONResponse({"status": "ready", "db": "ok"})
        
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix=API_PREFIX)
        
    return app

app = create_app()
