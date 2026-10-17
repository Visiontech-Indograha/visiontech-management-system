"""
app/modules/reports/services/weekly_report_service.py

Layanan logika bisnis untuk modul laporan mingguan pekerjaan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""

from app.services.weekly_report_service import (
    WeeklyReportService as BaseWeeklyReportService,
)


class WeeklyReportService(BaseWeeklyReportService):
    """
    Layanan bisnis laporan mingguan.
    Mengelola aturan pengisian draf, hak akses ketua, dan proses review mingguan oleh PM.
    """


__all__ = ["WeeklyReportService"]
