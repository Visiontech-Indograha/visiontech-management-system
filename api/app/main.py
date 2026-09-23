# Structured JSON logging
import json
import logging
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": request_id_context.get(None),
        }
        return json.dumps(log_record)

request_id_context = ContextVar("request_id", default=None)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)

setup_logging()
logger = logging.getLogger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
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
    async def health_check():
        return {"status": "ok"}
        
    @app.get("/ready")
    async def readiness_check():
        # TODO: Add db connection check here
        return {"status": "ready"}
        
    from app.api.assets import router as assets_router
    from app.api.attendance import router as attendance_router
    from app.api.attendance_cron import router as attendance_cron_router
    from app.api.audit import router as audit_router
    from app.api.auth import router as auth_router
    from app.api.documents import router as documents_router
    from app.api.employees import router as employees_router
    from app.api.expiry import router as expiry_router
    from app.api.files import router as files_router
    from app.api.hse import router as hse_router
    from app.api.plan_changes import router as changes_router
    from app.api.plan_transitions import router as transitions_router
    from app.api.plans import router as plans_router
    from app.api.sites import router as sites_router
    
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(audit_router, prefix=API_PREFIX)
    app.include_router(files_router, prefix=API_PREFIX)
    app.include_router(employees_router, prefix=API_PREFIX)
    app.include_router(documents_router, prefix=API_PREFIX)
    app.include_router(expiry_router, prefix=API_PREFIX)
    app.include_router(plans_router, prefix=API_PREFIX)
    app.include_router(transitions_router, prefix=API_PREFIX)
    app.include_router(changes_router, prefix=API_PREFIX)
    app.include_router(sites_router, prefix=API_PREFIX)
    app.include_router(attendance_router, prefix=API_PREFIX)
    app.include_router(attendance_cron_router, prefix=API_PREFIX)
    app.include_router(hse_router, prefix=API_PREFIX)
    app.include_router(assets_router, prefix=API_PREFIX)
        
    return app

app = create_app()
