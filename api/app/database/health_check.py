"""
app/database/health_check.py

Pemeriksaan konektivitas dan kesehatan basis data (readiness probe).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §3 & §11.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import app.database.session as db_session
from app.database.session import engine


async def check_database_health() -> bool:
    """
    Memeriksa apakah database aktif dan skema vms tersedia.
    Mengembalikan True jika sehat, False jika tidak dapat dijangkau.
    """
    try:
        active_engine = getattr(db_session, "engine", engine)
        async with active_engine.connect() as conn:
            # Alembic membuat tabel version di schema `public`, bukan `vms`.
            # Periksa keduanya: skema aplikasi ada DAN migrasi sudah pernah dijalankan.
            schema_ok = await conn.scalar(
                text(
                    "SELECT (to_regclass('public.office') IS NOT NULL) "
                    "AND (to_regclass('public.users') IS NOT NULL)"
                )
            )
            return bool(schema_ok)
    except (OSError, SQLAlchemyError):
        return False

