"""
app/core/errors.py
Penanganan error terpusat VMS.
Semua error bisnis dilempar sebagai AppError. Handler di main.py mengubahnya
menjadi bentuk baku dokumen 05 §2:
{ "error": { "code": "...", "message": "...", "details": {...} } }
dengan message Bahasa Indonesia untuk pengguna.
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Error bisnis yang bisa disampaikan ke klien."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}
        super().__init__(message)


# ── Kode error standar ─────────────────────────────────────────────────────────
class NotFoundError(AppError):
    def __init__(self, resource: str = "Data") -> None:
        super().__init__("NOT_FOUND", f"{resource} tidak ditemukan.", status=404)


class ForbiddenError(AppError):
    def __init__(self, reason: str = "Anda tidak memiliki akses.") -> None:
        super().__init__("FORBIDDEN", reason, status=403)


class ConflictError(AppError):
    """Dipakai untuk optimistic lock (row_version tidak cocok)."""
    def __init__(self, message: str = "Data sudah berubah. Muat ulang dan coba lagi.") -> None:
        super().__init__("CONFLICT", message, status=409)


class InvalidStateError(AppError):
    """Status dokumen tidak memungkinkan aksi ini."""
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_STATE", message, status=422)


class ValidationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("VALIDATION_ERROR", message, status=422)


class StorageError(AppError):
    def __init__(self, detail: str = "Gagal menyimpan berkas.") -> None:
        super().__init__("STORAGE_ERROR", detail, status=500)


# ── FastAPI exception handler ──────────────────────────────────────────────────
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )
