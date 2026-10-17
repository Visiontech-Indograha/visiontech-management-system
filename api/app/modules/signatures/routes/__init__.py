"""
Paket routing untuk modul signatures.
"""

from app.modules.signatures.routes.plan_document_route import (
    router as plan_documents_router,
)
from app.modules.signatures.routes.signature_route import router as signatures_router

__all__ = ["plan_documents_router", "signatures_router"]
