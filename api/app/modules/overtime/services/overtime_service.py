"""
app/modules/overtime/services/overtime_service.py

Layanan logika bisnis untuk modul lembur dan rekap lembur.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""

from app.services.overtime_service import OvertimeService as BaseOvertimeService


class OvertimeService(BaseOvertimeService):
    """
    Layanan bisnis lembur.
    Mengelola aturan pengajuan lembur, batas jam lembur, review PM/OPS, dan kalkulasi rekap bulanan.
    """


__all__ = ["OvertimeService"]
