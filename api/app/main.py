import uuid
import logging
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

# Structured JSON logging
import json

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

def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)
    
    app.add_middleware(RequestIDMiddleware)
    
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from app.core.errors import AppError, app_error_handler

    # AppError → { "error": { code, message, details } } (dok 05 §2)
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            error_payload = exc.detail
        else:
            code = "NOT_FOUND" if exc.status_code == 404 else "INVALID_CREDENTIALS" if exc.status_code == 401 else "FORBIDDEN" if exc.status_code == 403 else "BAD_REQUEST"
            error_payload = {
                "code": code,
                "message": str(exc.detail),
                "details": {}
            }
        return JSONResponse(status_code=exc.status_code, content={"error": error_payload})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        fields = {}
        for err in exc.errors():
            loc = ".".join(str(l) for l in err["loc"][1:])
            fields[loc] = err["msg"]
            
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Data yang dikirim tidak valid.",
                    "details": {"fields": fields}
                }
            }
        )
        
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Terjadi kesalahan internal pada server.",
                    "details": {}
                }
            }
        )

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
        
    @app.get("/ready")
    async def readiness_check():
        # TODO: Add db connection check here
        return {"status": "ready"}
        
    from app.api.auth import router as auth_router
    from app.api.audit import router as audit_router
    from app.api.files import router as files_router
    from app.api.employees import router as employees_router
    from app.api.documents import router as documents_router
    from app.api.expiry import router as expiry_router
    from app.api.plans import router as plans_router
    from app.api.plan_transitions import router as transitions_router
    from app.api.plan_changes import router as changes_router
    from app.api.sites import router as sites_router
    from app.api.attendance import router as attendance_router
    from app.api.attendance_cron import router as attendance_cron_router
    from app.api.hse import router as hse_router
    from app.api.assets import router as assets_router
    
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(files_router)
    app.include_router(employees_router)
    app.include_router(documents_router)
    app.include_router(expiry_router)
    app.include_router(plans_router)
    app.include_router(transitions_router)
    app.include_router(changes_router)
    app.include_router(sites_router)
    app.include_router(attendance_router)
    app.include_router(attendance_cron_router)
    app.include_router(hse_router)
    app.include_router(assets_router)
        
    return app

app = create_app()
