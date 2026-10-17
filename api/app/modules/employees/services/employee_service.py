"""
app/modules/employees/services/employee_service.py

Layanan logika bisnis untuk modul karyawan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""

from app.services.employee_service import (
    ARCHIVED,
    OFFBOARDED,
    RESTORED,
)
from app.services.employee_service import (
    EmployeeService as BaseEmployeeService,
)


class EmployeeService(BaseEmployeeService):
    """
    Layanan bisnis karyawan.
    Mengelola aturan promosi, mutasi, pengakhiran masa kerja, dan pemulihan status.
    """


__all__ = ["ARCHIVED", "OFFBOARDED", "RESTORED", "EmployeeService"]
