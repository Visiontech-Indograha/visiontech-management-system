"""
app/api/overtime.py
Router lembur (V-28) — domain.js REPORT_OVERTIME, REVIEW_OVERTIME + rekap bulanan.
Rute di bawah /work-plans/{plan_id}/overtime dan /overtime/recap.
Router tipis: hanya marshalling HTTP ↔ service.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_with_user
from app.schemas.overtime import (
    OvertimeCreate,
    OvertimeRecapRow,
    OvertimeResponse,
    OvertimeReview,
)
from app.services.overtime_service import OvertimeService

# Lembur per SK: POST /work-plans/{plan_id}/overtime, GET /work-plans/{plan_id}/overtime
plan_overtime_router = APIRouter(prefix="/work-plans/{plan_id}/overtime", tags=["Overtime"])

# Review per entri: POST /overtime/{ot_id}/review
# Rekap: GET /overtime/recap
overtime_router = APIRouter(prefix="/overtime", tags=["Overtime"])


@plan_overtime_router.post("", response_model=OvertimeResponse, status_code=status.HTTP_201_CREATED)
async def report_overtime(
    plan_id: UUID,
    data: OvertimeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> OvertimeResponse:
    """domain.js REPORT_OVERTIME (V-28): ketua atau anggota mengajukan lembur pada SK aktif."""
    row = await OvertimeService(db).report(current_user, plan_id, data.hours, data.reason)
    return OvertimeResponse(**row._mapping)


@plan_overtime_router.get("", response_model=list[OvertimeResponse])
async def list_overtime(
    plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> list[OvertimeResponse]:
    """Daftar lembur pada SK tertentu — siapa pun yang dapat melihat SK."""
    rows = await OvertimeService(db).list_by_plan(current_user, plan_id)
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


@overtime_router.get("/recap", response_model=list[OvertimeRecapRow])
async def overtime_recap(
    month: str | None = Query(
        default=None,
        description="Filter bulan dalam format YYYY-MM, contoh: 2026-09",
        pattern=r"^\d{4}-\d{2}$",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
) -> list[OvertimeRecapRow]:
    """Rekap lembur per karyawan per bulan — Finance, OPS, Admin (dok 03 M11)."""
    # Normalisasi: "2026-09" → "2026-09-01" agar cocok dengan period_month (date trunc)
    month_date = f"{month}-01" if month else None
    rows = await OvertimeService(db).recap(current_user, month_date)
    return [OvertimeRecapRow(**r._mapping) for r in rows]
