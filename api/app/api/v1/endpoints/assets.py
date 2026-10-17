"""
app/api/v1/endpoints/assets.py - Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.assets.routes.asset_route import router
from app.services.pdf_service import html_to_pdf

__all__ = ["html_to_pdf", "router"]
