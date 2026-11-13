"""Paket routing modul hikvision."""
from fastapi import APIRouter

from app.modules.hikvision.routes.admin_route import router as admin_router
from app.modules.hikvision.routes.penerima_route import router as penerima_router

router = APIRouter()
router.include_router(penerima_router)
router.include_router(admin_router)

__all__ = ["router"]
