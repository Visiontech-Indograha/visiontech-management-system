"""
Paket routing untuk modul system.
"""

from app.modules.system.routes.app_release_route import (
    router as app_releases_router,
)
from app.modules.system.routes.events_route import router as events_router
from app.modules.system.routes.files_route import router as files_router
from app.modules.system.routes.monitoring_route import (
    router as monitoring_router,
)
from app.modules.system.routes.sync_route import router as sync_router

__all__ = [
    "app_releases_router",
    "events_router",
    "files_router",
    "monitoring_router",
    "sync_router",
]
