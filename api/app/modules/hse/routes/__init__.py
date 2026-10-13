"""
Paket routing untuk modul HSE.
"""
from app.modules.hse.routes.daily_report_route import days_router as daily_report_router
from app.modules.hse.routes.hse_incident_route import router as hse_router

__all__ = ["daily_report_router", "hse_router"]
