from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user, require_permission
from app.core.errors import AppError
from app.core.permissions import Permission
from app.schemas.attendance import GeoPoint, SiteCreate, SiteResponse

router = APIRouter(prefix="/sites", tags=["Sites"])

@router.get("", response_model=list[SiteResponse])
async def get_sites(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
) -> list[SiteResponse]:
    query = text("""
        SELECT id, name, address, radius_m, 
               ST_Y(location::geometry) as lat, ST_X(location::geometry) as lng
        FROM vms.site
        WHERE organization_id = :org AND deleted_at IS NULL
        ORDER BY name ASC
    """)
    rows = (await db.execute(query, {"org": current_user.organization_id})).fetchall()
    
    return [
        SiteResponse(
            id=r.id, name=r.name, address=r.address, radius_m=r.radius_m or 50,
            location=GeoPoint(lat=r.lat, lng=r.lng)
        ) for r in rows
    ]

@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    data: SiteCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)), # Or MANAGE_SITES
    db: AsyncSession = Depends(get_db_with_user)
) -> SiteResponse:
    query = text("""
        INSERT INTO vms.site (organization_id, name, address, radius_m, location)
        VALUES (:org, :name, :addr, :rad, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
        RETURNING id, name, address, radius_m, ST_Y(location::geometry) as lat, ST_X(location::geometry) as lng
    """)
    try:
        res = await db.execute(query, {
            "org": current_user.organization_id, "name": data.name,
            "addr": data.address, "rad": data.radius_m,
            "lng": data.location.lng, "lat": data.location.lat
        })
        r = res.one()
    except Exception as e:
        # Jangan bocorkan pesan basis data mentah ke klien (dok 12: galat berbahasa Indonesia).
        raise AppError("SITE_INVALID", "Lokasi tidak dapat disimpan. Periksa nama dan koordinat.",
                       status=400) from e
    return SiteResponse(
        id=r.id, name=r.name, address=r.address, radius_m=r.radius_m or 50,
        location=GeoPoint(lat=r.lat, lng=r.lng)
    )

@router.delete("/{site_id}")
async def delete_site(
    site_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    db: AsyncSession = Depends(get_db_with_user)
) -> dict[str, str]:
    query = text("UPDATE vms.site SET deleted_at = now() WHERE id = :id AND organization_id = :org")
    await db.execute(query, {"id": site_id, "org": current_user.organization_id})
    return {"message": "Site deleted"}
