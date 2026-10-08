"""
app/core/errors.py
Penanganan error terpusat VMS.
Semua error bisnis dilempar sebagai AppError. Handler di main.py mengubahnya
menjadi bentuk baku dokumen 05 §2:
{ "error": { "code": "...", "message": "...", "details": {...} } }
dengan message Bahasa Indonesia untuk pengguna.
"""
from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """
    Error bisnis yang bisa disampaikan ke klien.

    `persist=True`: permintaan ditolak, tetapi perubahan data yang sudah dibuat dalam
    transaksinya tetap disimpan — mis. catatan percobaan login gagal (dasar penguncian)
    atau pencabutan rantai sesi saat refresh token dipakai ulang.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        details: dict[str, Any] | None = None,
        persist: bool = False,
    ) -> None:
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}
        self.persist = persist
        super().__init__(message)


# ── Kode error standar ─────────────────────────────────────────────────────────
class NotFoundError(AppError):
    """Galat jika sumber daya/data tidak ditemukan (HTTP 404)."""
    def __init__(self, resource: str = "Data") -> None:
        super().__init__("NOT_FOUND", f"{resource} tidak ditemukan.", status=404)


class ForbiddenError(AppError):
    """Galat jika pengguna tidak memiliki hak akses (HTTP 403)."""
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
    """Galat validasi aturan bisnis atau payload masukan (HTTP 422)."""
    def __init__(self, message: str) -> None:
        super().__init__("VALIDATION_ERROR", message, status=422)


class StorageError(AppError):
    """Galat ketika berinteraksi dengan penyimpanan (S3/minio) (HTTP 500)."""
    def __init__(self, detail: str = "Gagal menyimpan berkas.") -> None:
        super().__init__("STORAGE_ERROR", detail, status=500)


def trigger_rule_message(exc: BaseException) -> str | None:
    """Pesan aturan bisnis dari trigger kita (`RAISE EXCEPTION '…' USING ERRCODE = '23514'`, db/02),
    atau None. CHECK constraint biasa juga 23514 tetapi membawa `constraint_name` dan pesan bahasa
    Inggris — itu tetap disembunyikan sebagai DB_ERROR."""
    cause = getattr(getattr(exc, "orig", None), "__cause__", None)
    if getattr(cause, "sqlstate", None) == "23514" and not getattr(cause, "constraint_name", None):
        message = getattr(cause, "message", None)
        return str(message) if message else None
    return None


# Kode 23xxx yang dipakai `RAISE EXCEPTION` di trigger kita (db/02) → galat untuk pengguna.
_TRIGGER_CODES: dict[str, tuple[str, int]] = {
    "23514": ("VALIDATION_ERROR", 422),     # aturan data (SIM, radius, dokumen terkunci, …)
    "23505": ("PERSONNEL_CONFLICT", 409),   # bentrok jadwal personel (tg_member_no_conflict)
    "23503": ("NOT_FOUND", 404),            # rujukan tanda tangan tidak dikenal
}


def trigger_rule_error(exc: BaseException) -> AppError | None:
    """AppError berisi pesan Indonesia dari trigger kita, atau None bila galatnya bukan dari trigger
    (pelanggaran constraint sungguhan membawa `constraint_name` — tetap disembunyikan)."""
    cause = getattr(getattr(exc, "orig", None), "__cause__", None)
    sqlstate = getattr(cause, "sqlstate", None)
    message = getattr(cause, "message", None)
    if sqlstate in _TRIGGER_CODES and message and not getattr(cause, "constraint_name", None):
        code, status = _TRIGGER_CODES[sqlstate]
        return AppError(code, str(message), status=status)
    return None


# ── FastAPI exception handler ──────────────────────────────────────────────────
def _error_response(status: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.status, exc.code, exc.message, exc.details)


# Kode & pesan bawaan per status HTTP (dok 05 §2). Pesan untuk orang lapangan, bukan programmer.
_STATUS_DEFAULTS: dict[int, tuple[str, str]] = {
    400: ("BAD_REQUEST", "Permintaan tidak dapat diproses."),
    401: ("UNAUTHENTICATED", "Sesi berakhir. Silakan masuk kembali."),
    403: ("FORBIDDEN", "Anda tidak memiliki akses untuk tindakan ini."),
    404: ("NOT_FOUND", "Data atau halaman tidak ditemukan."),
    405: ("METHOD_NOT_ALLOWED", "Metode tidak didukung untuk alamat ini."),
    409: ("CONFLICT", "Data ini baru saja diubah. Muat ulang lalu coba lagi."),
    413: ("PAYLOAD_TOO_LARGE", "Ukuran data terlalu besar."),
    422: ("VALIDATION_ERROR", "Ada isian yang belum benar. Periksa kembali."),
    429: ("TOO_MANY_REQUESTS", "Terlalu banyak permintaan. Coba lagi beberapa saat lagi."),
}
_INTERNAL = ("INTERNAL_ERROR", "Terjadi gangguan pada sistem. Coba lagi beberapa saat; bila berulang, hubungi admin.")
_DB_ERROR_MESSAGE = "Data tidak dapat disimpan karena bertentangan dengan data lain. Periksa isian lalu coba lagi."


def _defaults_for(status: int) -> tuple[str, str]:
    if status >= 500:
        return _INTERNAL
    return _STATUS_DEFAULTS.get(status, ("BAD_REQUEST", _STATUS_DEFAULTS[400][1]))


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = _defaults_for(exc.status_code)
    details: dict[str, Any] = {}
    detail = exc.detail

    if exc.status_code >= 500:
        # Isi galat internal tidak pernah dikirim ke klien; detailnya hanya di log.
        logger.error("HTTP %s: %s", exc.status_code, detail)
    elif isinstance(detail, dict):
        code = str(detail.get("code") or code)
        details = dict(detail.get("details") or {})
        if code == "DB_ERROR":
            # Hanya baris pertama: sisanya "[SQL: …] [parameters: …]" memuat data pribadi (dok 08).
            logger.error("DB_ERROR: %s", str(detail.get("message") or "").split("\n", 1)[0])
            message = _DB_ERROR_MESSAGE
        else:
            message = str(detail.get("message") or message)
    elif isinstance(detail, str) and detail and detail != HTTPStatus(exc.status_code).phrase:
        message = detail  # pesan yang ditulis aplikasi (Bahasa Indonesia)

    return _error_response(exc.status_code, code, message, details)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = {".".join(str(part) for part in err["loc"][1:]): err["msg"] for err in exc.errors()}
    return _error_response(422, "VALIDATION_ERROR", _STATUS_DEFAULTS[422][1], {"fields": fields})


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error: %s", exc, exc_info=exc)
    return _error_response(500, *_INTERNAL)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
