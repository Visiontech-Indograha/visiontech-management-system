"""
app/crud/crud_site.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.sites.repositories.site_repository import CRUDSite, SiteRepository

__all__ = ["CRUDSite", "SiteRepository"]
