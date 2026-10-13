"""
app/core/logging_config.py

Konfigurasi logging terstruktur (JSON) dan penelusuran request ID.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §3 & §13.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Konteks untuk menyimpan request ID secara asinkron (per request)
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


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


def setup_logging() -> None:
    """
    Mengatur konfigurasi logging dasar aplikasi untuk menggunakan format JSON.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware untuk menyisipkan request ID yang unik di setiap siklus HTTP request/response.
    Berguna untuk penelusuran (tracing) log per request.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Memproses request, menetapkan request ID, dan mengembalikan response."""
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_context.set(req_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

