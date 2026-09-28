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

        from app.db.session import engine

        try:
            async with engine.connect() as conn:
                schema_ok = await conn.scalar(text("SELECT to_regclass('vms.organization') IS NOT NULL"))
        except (OSError, SQLAlchemyError):
            schema_ok = None
        if not schema_ok:
            return JSONResponse({"status": "not_ready", "db": "unreachable"}, status_code=503)
        return JSONResponse({"status": "ready", "db": "ok"})
        
    from app.api.accounts import router as accounts_router
    from app.api.assets import plan_assets_router
    from app.api.assets import router as assets_router
    from app.api.attendance import router as attendance_router
    from app.api.attendance_cron import router as attendance_cron_router
    from app.api.audit import router as audit_router
    from app.api.auth import router as auth_router
    from app.api.documents import router as documents_router
    from app.api.employees import router as employees_router
    from app.api.expiry import router as expiry_router
    from app.api.files import router as files_router
    from app.api.hse import days_router as daily_report_router
    from app.api.hse import router as hse_router
    from app.api.monitoring import router as monitoring_router
    from app.api.overtime import overtime_router
    from app.api.overtime import recaps_router as overtime_recaps_router
    from app.api.plan_attachments import router as plan_attachments_router
    from app.api.plan_changes import plan_router as plan_changes_router
    from app.api.plan_changes import router as changes_router
    from app.api.plan_days import router as plan_days_router
    from app.api.plan_location import router as plan_location_router
    from app.api.plan_members import router as plan_members_router
    from app.api.plan_transitions import router as transitions_router
    from app.api.plans import router as plans_router
    from app.api.signatures import plan_documents_router
    from app.api.signatures import router as signatures_router
    from app.api.sites import router as sites_router
    from app.api.sync import router as sync_router
    from app.api.units import router as units_router
    from app.api.weekly_reports import router as weekly_reports_router

    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(audit_router, prefix=API_PREFIX)
    app.include_router(files_router, prefix=API_PREFIX)
    app.include_router(employees_router, prefix=API_PREFIX)
    app.include_router(documents_router, prefix=API_PREFIX)
    app.include_router(expiry_router, prefix=API_PREFIX)
    app.include_router(plans_router, prefix=API_PREFIX)
    app.include_router(plan_members_router, prefix=API_PREFIX)
    app.include_router(transitions_router, prefix=API_PREFIX)
    app.include_router(plan_changes_router, prefix=API_PREFIX)
    app.include_router(changes_router, prefix=API_PREFIX)
    app.include_router(sites_router, prefix=API_PREFIX)
    app.include_router(units_router, prefix=API_PREFIX)
    app.include_router(accounts_router, prefix=API_PREFIX)
    app.include_router(sync_router, prefix=API_PREFIX)
    app.include_router(plan_location_router, prefix=API_PREFIX)
    app.include_router(weekly_reports_router, prefix=API_PREFIX)
    app.include_router(monitoring_router, prefix=API_PREFIX)
    app.include_router(plan_attachments_router, prefix=API_PREFIX)
    app.include_router(plan_days_router, prefix=API_PREFIX)
    app.include_router(plan_documents_router, prefix=API_PREFIX)
    app.include_router(signatures_router, prefix=API_PREFIX)
    app.include_router(attendance_router, prefix=API_PREFIX)
    app.include_router(attendance_cron_router, prefix=API_PREFIX)
    app.include_router(hse_router, prefix=API_PREFIX)
    app.include_router(daily_report_router, prefix=API_PREFIX)
    app.include_router(assets_router, prefix=API_PREFIX)
    app.include_router(plan_assets_router, prefix=API_PREFIX)
    app.include_router(overtime_router, prefix=API_PREFIX)
    app.include_router(overtime_recaps_router, prefix=API_PREFIX)
        
    return app

app = create_app()
