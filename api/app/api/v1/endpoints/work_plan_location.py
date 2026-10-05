"""Lokasi penugasan SK: cari kota → tetapkan titik koordinat & radius absensi (revisi PM 2026-09-26)."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_plan_location_service, plan_access, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.plan_location import GeoResult, PlanLocationIn, PlanLocationOut
from app.services.access_service import PlanAccess, PlanNeed
from app.services.geocode_service import GeocodeService
from app.services.plan_location_service import PlanLocationService

router = APIRouter(tags=["Plan Location"])
_VIEW = Depends(plan_access(PlanNeed.VIEW))
_PM_UNIT = Depends(plan_access(PlanNeed.PM_UNIT))








@router.get("/geo/search", response_model=list[GeoResult])
async def geo_search(q: str = Query(min_length=1, max_length=120),
                     _: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN))) -> list[GeoResult]:
    """
    Pencarian kota/tempat di Indonesia berdasarkan kueri (Nominatim, di-cache) (GET).
    Hanya untuk pengelola SK.
    
    Query Parameters:
    - q (str): Kata kunci lokasi yang dicari.
    
    Returns:
    - list[GeoResult]: Daftar hasil pencarian lokasi (koordinat dan nama wilayah).
    """
    # Memastikan hak akses CREATE_PLAN melalui Dependency Injection
    # Meneruskan kueri pencarian ke layanan GeocodeService
    return [GeoResult(**r) for r in await GeocodeService().search(q)]


@router.get("/work-plans/{plan_id}/location", response_model=PlanLocationOut | None)
async def get_plan_location(access: PlanAccess = _VIEW,
                            plan_location_service: PlanLocationService = Depends(get_plan_location_service)) -> PlanLocationOut | None:
    """
    Mengambil lokasi titik absensi untuk sebuah rencana kerja (SK) (GET).
    
    Path Parameters:
    - plan_id (UUID): ID dari rencana kerja (SK).
    
    Returns:
    - PlanLocationOut | None: Koordinat titik absensi atau null bila belum disetel.
    """
    # Memeriksa akses baca (VIEW) menggunakan Dependency Injection
    # Mengambil data lokasi melalui layer Service
    row = await plan_location_service.location(access)
    return None if row is None else PlanLocationOut(**row)


@router.put("/work-plans/{plan_id}/location", response_model=PlanLocationOut)
async def set_plan_location(data: PlanLocationIn,
                            access: PlanAccess = _PM_UNIT,
                            plan_location_service: PlanLocationService = Depends(get_plan_location_service)) -> PlanLocationOut:
    """
    Menyetel titik absensi (lokasi) untuk rencana kerja (PUT).
    SK draf maupun berjalan; teks lokasi dokumen tetap, hanya titik absensi yang berubah.
    
    Path Parameters:
    - plan_id (UUID): ID dari rencana kerja.
    
    Request Body:
    - data (PlanLocationIn): Data nama lokasi, alamat, latitude, longitude, dan radius absensi.
    
    Returns:
    - PlanLocationOut: Data lokasi terbaru.
    """
    # Dependency Injection untuk memastikan pengguna bertindak sebagai PM_UNIT
    # Memanggil method layer Service untuk menyimpan pengaturan lokasi
    row = await plan_location_service.set_location(
        access, name=data.name, address=data.address, lat=data.lat, lng=data.lng, radius_m=data.radius_m)
    return PlanLocationOut(**row)
