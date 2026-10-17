"""
app/api/v1/endpoints/face.py - Shim re-export untuk modul face modular.
"""
from app.modules.face.routes.face_route import router

__all__ = ["router"]
