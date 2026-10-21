"""
app/modules/employees/dependencies.py
Perakitan service modul employees (satu permintaan = satu transaksi).
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.employees.repositories.employee_repository import EmployeeRepository
from app.modules.employees.services.employee_service import EmployeeService


def get_employee_service(db: AsyncSession = Depends(get_db_with_user)) -> EmployeeService:
    return EmployeeService(EmployeeRepository(db))
