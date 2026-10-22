"""
Paket routing untuk modul auth.
Menggabungkan rute login, profile, dan session ke router modular terpadu.
"""

from fastapi import APIRouter

from app.modules.auth.routes.auth_login_route import router as login_router
from app.modules.auth.routes.auth_profile_route import router as profile_router
from app.modules.auth.routes.auth_session_route import router as session_router

router = APIRouter()

router.include_router(login_router)
router.include_router(profile_router)
router.include_router(session_router)

__all__ = ["router"]
