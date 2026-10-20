"""
app/api/v1/endpoints/signatures.py - Shim re-export untuk kompatibilitas uji lama.
"""
from collections import defaultdict, deque

from app.modules.signatures.routes.signature_route import router
from app.shared.documents.pdf_service import html_to_pdf

VERIFY_LIMIT = 30
VERIFY_WINDOW = 60.0
_verify_hits: dict[str, deque[float]] = defaultdict(deque)

__all__ = ["VERIFY_LIMIT", "VERIFY_WINDOW", "_verify_hits", "html_to_pdf", "router"]
