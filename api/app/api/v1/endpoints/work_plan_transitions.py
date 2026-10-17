"""
app/api/v1/endpoints/work_plan_transitions.py - Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.work_plans.routes.work_plan_transitions_route import router
from app.services.pdf_service import html_to_pdf

__all__ = ["html_to_pdf", "router"]
