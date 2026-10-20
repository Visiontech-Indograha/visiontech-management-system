"""
app/modules/sites/schemas/site_schema.py

Skema master kantor (tabel `office`): kantor utama & cabang beserta radius presensi, batas kota,
jam kerja, dan tarif uang makan (docs/35 §5).
"""

from datetime import time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.attendance.schemas.attendance_schema import GeoPoint


class SiteCreate(BaseModel):
    """Kantor baru (pusat/cabang)."""

    name: str = Field(min_length=2, max_length=100)
    address: str | None = Field(default=None, max_length=500)
    location: GeoPoint
    radius_m: int = Field(100, ge=10, le=5000)                       # office.attendance_radius_m
    city_boundary_radius_m: int = Field(15000, ge=1000, le=200000)   # batas "dalam kota" kantor utama
    clock_in_time: time = time(7, 0)
    clock_out_time: time = time(16, 0)
    in_city_meal_rate: Decimal = Field(Decimal("35000.00"), ge=0)
    out_city_meal_rate: Decimal = Field(Decimal("65000.00"), ge=0)
    is_main_office: bool = False


class SiteUpdate(BaseModel):
    """Perubahan sebagian data kantor; field kosong tidak diubah."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    address: str | None = Field(default=None, max_length=500)
    location: GeoPoint | None = None
    radius_m: int | None = Field(default=None, ge=10, le=5000)
    city_boundary_radius_m: int | None = Field(default=None, ge=1000, le=200000)
    clock_in_time: time | None = None
    clock_out_time: time | None = None
    in_city_meal_rate: Decimal | None = Field(default=None, ge=0)
    out_city_meal_rate: Decimal | None = Field(default=None, ge=0)
    is_main_office: bool | None = None


class SiteResponse(SiteCreate):
    """Kantor sebagaimana tersimpan."""

    id: UUID
    # Selalu None di V2 (lokasi proyek ada di work_plan_daily); dipertahankan untuk klien lama.
    unit_id: UUID | None = None
    # Peminta boleh mengubah/menghapus kantor ini (izin manage:sites)
    can_manage: bool = False


__all__ = ["GeoPoint", "SiteCreate", "SiteResponse", "SiteUpdate"]
