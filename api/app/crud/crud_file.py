"""
app/crud/crud_file.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.system.repositories.file_repository import CRUDFile, FileRepository

__all__ = ["CRUDFile", "FileRepository"]
