"""
app/modules/employees/dependencies.py

Perakitan service modul employees untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.employees.services.employee_service import EmployeeService


def get_employee_service(db: AsyncSession = Depends(get_db_with_user)) -> EmployeeService:
    return EmployeeService(db)
