"""
app/modules/sites/schemas/site_schema.py

Skema data lokasi kerja (koordinat, radius, nama lokasi).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.5.
"""
from app.schemas.attendance import GeoPoint, SiteCreate, SiteResponse

__all__ = [
    "GeoPoint",
    "SiteCreate",
    "SiteResponse",
]
