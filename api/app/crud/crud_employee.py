"""
app/crud/crud_employee.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.employees.repositories.employee_repository import (
    CRUDEmployee,
    EmployeeRepository,
)

__all__ = ["CRUDEmployee", "EmployeeRepository"]
