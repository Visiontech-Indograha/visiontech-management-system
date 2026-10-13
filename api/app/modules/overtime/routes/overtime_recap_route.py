"""
app/modules/overtime/routes/overtime_recap_route.py

Rute endpoint HTTP untuk rekapitulasi lembur (/recaps/overtime).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.overtime.controllers.overtime_controller import OvertimeController
from app.modules.overtime.schemas.overtime_schema import OvertimeRecapRow

router = APIRouter(prefix="/recaps", tags=["Overtime"])


@router.get("/overtime", response_model=list[OvertimeRecapRow])
async def overtime_recap(
    month: str | None = Query(
        default=None,
        description="Filter bulan dalam format YYYY-MM, contoh: 2026-09",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    controller: OvertimeController = Depends(),
) -> list[OvertimeRecapRow]:
    """Rekap lembur per karyawan per bulan."""
    return await controller.handle_recap(current_user, month)
