"""
app/crud/crud_face.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.face.repositories.face_repository import CRUDFace, FaceRepository

__all__ = ["CRUDFace", "FaceRepository"]
