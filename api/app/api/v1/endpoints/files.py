"""
app/api/v1/endpoints/files.py - Shim re-export untuk kompatibilitas uji lama.
"""
from app.core.storage import upload_file
from app.modules.system.controllers.files_controller import ALLOWED_MIMES, MAX_FILE_SIZE
from app.modules.system.routes.files_route import router

__all__ = ["ALLOWED_MIMES", "MAX_FILE_SIZE", "router", "upload_file"]
