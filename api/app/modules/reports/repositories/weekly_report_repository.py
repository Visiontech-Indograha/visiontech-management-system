"""
app/modules/reports/repositories/weekly_report_repository.py

Repositori data laporan mingguan pekerjaan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""
from app.crud.crud_weekly_report import CRUDWeeklyReport


class WeeklyReportRepository(CRUDWeeklyReport):
    """
    Repositori akses data penyimpanan, penyerahan, dan peninjauan laporan mingguan.
    """
