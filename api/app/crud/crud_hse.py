"""
app/crud/crud_hse.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.hse.repositories.hse_repository import CRUDHse, HseRepository

__all__ = ["CRUDHse", "HseRepository"]
