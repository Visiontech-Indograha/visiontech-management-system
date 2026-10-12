"""
app/modules/sites/repositories/site_repository.py

Repository akses data persistensi untuk lokasi kerja (vms.site).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.4.
"""
from app.crud.crud_site import CRUDSite


class SiteRepository(CRUDSite):
    """
    Repository akses data tabel vms.site.
    """
