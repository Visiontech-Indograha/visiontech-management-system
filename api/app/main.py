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
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}
        )

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
        
    @app.get("/ready")
    async def readiness_check():
        # TODO: Add db connection check here
        return {"status": "ready"}
        
    from app.api.auth import router as auth_router
    app.include_router(auth_router)
        
    return app

app = create_app()
