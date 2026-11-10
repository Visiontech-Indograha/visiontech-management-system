"""Rute penyiapan awal (PUBLIK, tanpa login). Aman karena: kode penyiapan dari env, hanya berhasil bila belum ada
SUPER_ADMIN aktif, rate limit selalu aktif, dan terkunci permanen sesudahnya."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.rate_limit import GROUP_SETUP, rate_limit
from app.modules.setup.dependencies import get_setup_service
from app.modules.setup.schemas.setup_schema import SetupAdminIn, SetupAdminOut, SetupStatusOut
from app.modules.setup.services.setup_service import SetupService

router = APIRouter(prefix="/setup", tags=["Setup"], dependencies=[Depends(rate_limit(GROUP_SETUP, always=True))])


@router.get("/status", response_model=SetupStatusOut)
async def setup_status(service: SetupService = Depends(get_setup_service)) -> SetupStatusOut:
    """Apakah instalasi ini belum punya admin (perlu penyiapan awal)."""
    return await service.status()


@router.post("/admin", response_model=SetupAdminOut, status_code=status.HTTP_201_CREATED)
async def setup_admin(data: SetupAdminIn, service: SetupService = Depends(get_setup_service)) -> SetupAdminOut:
    """Buat Super Admin pertama. 404 bila SETUP_TOKEN tidak diisi, 403 kode salah, 409 bila sudah ada admin."""
    return await service.create_admin(data)
