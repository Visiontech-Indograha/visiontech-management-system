"""
Paket routing untuk modul overtime.
"""

from app.modules.overtime.routes.overtime_recap_route import router as overtime_recaps_router
from app.modules.overtime.routes.overtime_route import router as overtime_router

__all__ = ["overtime_recaps_router", "overtime_router"]
