"""
app/modules/reports/dependencies.py

Perakitan service modul reports untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.reports.services.weekly_report_service import WeeklyReportService


def get_weekly_report_service(db: AsyncSession = Depends(get_db_with_user)) -> WeeklyReportService:
    return WeeklyReportService(db)
