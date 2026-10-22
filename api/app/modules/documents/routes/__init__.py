"""
Paket routing untuk modul documents.
"""

from app.modules.documents.routes.document_expiry_route import router as expiry_router
from app.modules.documents.routes.employee_document_route import router as documents_router

__all__ = ["documents_router", "expiry_router"]
