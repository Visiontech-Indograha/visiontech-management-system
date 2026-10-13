"""
Paket routing untuk modul assets.
"""
from app.modules.assets.routes.asset_route import router as assets_router
from app.modules.assets.routes.plan_asset_route import plan_assets_router

__all__ = ["assets_router", "plan_assets_router"]
