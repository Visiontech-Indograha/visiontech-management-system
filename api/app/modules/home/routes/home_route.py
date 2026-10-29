"""
app/modules/home/routes/home_route.py

Rute ringkasan Beranda (/home/summary).
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.home.controllers.home_controller import HomeController
from app.modules.home.schemas.home_schema import HomeSummary

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/summary", response_model=HomeSummary, summary="Ringkasan Beranda sesuai peran")
async def home_summary(
    current_user: CurrentUser = Depends(get_current_user),
    controller: HomeController = Depends(),
) -> HomeSummary:
    """Jumlah pekerjaan yang menunggu tindakan pengguna (cuti, absensi, lembur, mess, aset, koreksi, offboarding)."""
    return await controller.handle_summary(current_user)
