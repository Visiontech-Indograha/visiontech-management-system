"""
app/modules/overtime/repositories/overtime_repository.py

Repositori data lembur dan rekap lembur.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""

from app.crud.crud_overtime import CRUDOvertime


class OvertimeRepository(CRUDOvertime):
    """
    Repositori akses data pengajuan lembur, peninjauan lembur, dan rekap bulanan lembur.
    """
