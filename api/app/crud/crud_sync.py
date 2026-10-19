"""
app/crud/crud_sync.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.system.repositories.sync_repository import CRUDSync, SyncRepository

__all__ = ["CRUDSync", "SyncRepository"]
