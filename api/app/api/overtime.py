"""
app/api/overtime.py
Router lembur (V-28, dok 05 §3.8 & §3.13) — domain.js REPORT_OVERTIME, REVIEW_OVERTIME + rekap bulanan.
Jalur: POST/GET /overtime, POST /overtime/{id}/review, GET /recaps/overtime.
Router tipis: hanya marshalling HTTP ↔ service.
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user
from app.api.guards import ensure_same_org
from app.schemas.overtime import (
    OvertimeCreate,
    OvertimeRecapRow,
    OvertimeResponse,
    OvertimeReview,
)
from app.services.overtime_service import OvertimeService

overtime_router = APIRouter(prefix="/overtime", tags=["Overtime"])
recaps_router = APIRouter(prefix="/recaps", tags=["Overtime"])


@overtime_router.post("", response_model=OvertimeResponse, status_code=status.HTTP_201_CREATED)
async def report_overtime(
    data: OvertimeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> OvertimeResponse:
    """domain.js REPORT_OVERTIME (V-28): ketua atau anggota mengajukan lembur pada SK aktif."""
    await ensure_same_org(db, current_user.organization_id, work_plans=[data.work_plan_id])
    row = await OvertimeService(db).report(current_user, data.work_plan_id, data.hours, data.reason)
    return OvertimeResponse(**row._mapping)


@overtime_router.get("", response_model=list[OvertimeResponse])
async def list_overtime(
    work_plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> list[OvertimeResponse]:
    """Daftar lembur satu SK — siapa pun yang dapat melihat SK (tidak terlihat → 404)."""
    rows = await OvertimeService(db).list_by_plan(current_user, work_plan_id)
    return [OvertimeResponse(**r._mapping) for r in rows]


@overtime_router.post("/{ot_id}/review", response_model=OvertimeResponse)
async def review_overtime(
    ot_id: UUID,
    data: OvertimeReview,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> OvertimeResponse:
    """domain.js REVIEW_OVERTIME (V-28): PM unit/OPS menyetujui atau menolak lembur PENDING_PM."""
    row = await OvertimeService(db).review(current_user, ot_id, data.decision, data.note)
    return OvertimeResponse(**row._mapping)


@recaps_router.get("/overtime", response_model=list[OvertimeRecapRow])
async def overtime_recap(
    month: str | None = Query(
        default=None,
        description="Filter bulan dalam format YYYY-MM, contoh: 2026-09",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> list[OvertimeRecapRow]:
    """Rekap lembur per karyawan per bulan — Finance/OPS/Admin seluruh organisasi, PM unitnya (dok 10 V-28)."""
    # asyncpg butuh objek date untuk CAST(:month AS date); period_month = date_trunc('month', work_date)
    month_date = date.fromisoformat(f"{month}-01") if month else None
    rows = await OvertimeService(db).recap(current_user, month_date)
    return [OvertimeRecapRow(**r._mapping) for r in rows]
