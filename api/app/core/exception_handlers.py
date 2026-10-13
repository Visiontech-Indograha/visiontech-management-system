"""
app/core/exception_handlers.py

Pendaftaran exception handlers terpusat untuk FastAPI.
Menerjemahkan AppError, validasi Pydantic, dan galat HTTP ke respons standar.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §3 & §8.
"""
from fastapi import FastAPI

from app.core.errors import register_error_handlers


def register_exception_handlers(app: FastAPI) -> None:
    """
    Mendaftarkan semua exception handler standar aplikasi ke instance FastAPI.
    """
    register_error_handlers(app)

