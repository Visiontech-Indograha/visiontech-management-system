"""
Paket routing untuk modul reports.
"""

from app.modules.reports.routes.weekly_report_route import (
    router as weekly_reports_router,
)

__all__ = ["weekly_reports_router"]
