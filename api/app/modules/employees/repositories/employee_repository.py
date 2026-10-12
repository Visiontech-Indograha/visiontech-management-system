"""
app/modules/employees/repositories/employee_repository.py

Repositori data karyawan (abstraksi akses data/SQL).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""
from app.crud.crud_employee import CRUDEmployee


class EmployeeRepository(CRUDEmployee):
    """
    Repositori akses data karyawan.
    Menyediakan operasi query SQL statis dan manipulasi status karyawan.
    """
