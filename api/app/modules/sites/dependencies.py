"""
app/modules/sites/dependencies.py

Perakitan service modul sites untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.sites.repositories.site_repository import CRUDSite
from app.modules.sites.services.site_service import SiteService


def get_site_service(db: AsyncSession = Depends(get_db_with_user)) -> SiteService:
    return SiteService(CRUDSite(db))
