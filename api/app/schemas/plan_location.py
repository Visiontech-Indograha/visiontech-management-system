"""Skema permintaan & respons: plan location (dipindah dari api/v1/endpoints/work_plan_location.py, R-28 M2b)."""
from uuid import UUID

from pydantic import BaseModel, Field


class GeoResult(BaseModel):
    """Hasil pencarian atau geokode dari lokasi."""
    name: str  # Nama lokasi
    lat: float  # Titik lintang koordinat lokasi (latitude)
    lng: float  # Titik bujur koordinat lokasi (longitude)
    type: str  # Tipe hasil pencarian


class PlanLocationIn(BaseModel):
    """Permintaan penambahan atau pengubahan lokasi untuk Rencana Kerja."""
    name: str = Field(min_length=1, max_length=200)  # Nama dari lokasi
    address: str | None = Field(default=None, max_length=500)  # Alamat jalan dari lokasi
    lat: float = Field(ge=-90, le=90)  # Koordinat lintang (latitude)
    lng: float = Field(ge=-180, le=180)  # Koordinat bujur (longitude)
    radius_m: int = 100  # Radius efektif (dalam meter) untuk keperluan absensi/presensi
    reason: str | None = Field(default=None, max_length=500)  # Alasan; wajib bila rencana kerja sudah terbit


class PlanLocationOut(BaseModel):
    """Respons informasi lokasi suatu Rencana Kerja."""
    id: UUID  # ID lokasi
    name: str  # Nama lokasi
    address: str | None  # Alamat dari lokasi
    lat: float  # Titik lintang lokasi
    lng: float  # Titik bujur lokasi
    radius_m: int | None  # Jari-jari (radius) dalam meter untuk lokasi kerja
