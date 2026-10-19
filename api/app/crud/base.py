"""
app/crud/base.py
Kelas dasar untuk semua crud (Shim re-export ke app.core.repository).
"""

from __future__ import annotations

from app.core.repository import BaseRepository, CRUDBase

__all__ = ["BaseRepository", "CRUDBase"]
