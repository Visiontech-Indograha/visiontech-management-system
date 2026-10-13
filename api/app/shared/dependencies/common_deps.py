"""
app/shared/dependencies/common_deps.py

Dependency umum yang dipakai bersama oleh endpoint: sesi database, pagination cursor, dsb.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.7.
"""
from app.database.session import get_db_session

__all__ = [
    "get_db_session",
]

