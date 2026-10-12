"""
app/database/session.py

Koneksi database dan sesi asynchronous.
Mengonfigurasi async engine, session maker, transaction boundary (unit of work),
dan konteks request untuk Row Level Security (RLS) & audit.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §3 & §9.
"""
from app.db.session import (
    SEARCH_PATH,
    AsyncSessionLocal,
    engine,
    get_db_session,
    make_engine,
    set_request_context,
    unit_of_work,
)

__all__ = [
    "SEARCH_PATH",
    "AsyncSessionLocal",
    "engine",
    "get_db_session",
    "make_engine",
    "set_request_context",
    "unit_of_work",
]

