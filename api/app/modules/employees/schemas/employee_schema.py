"""
app/modules/employees/schemas/employee_schema.py

Skema validasi permintaan dan respons data karyawan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""
from app.schemas.employee import (
    AttendanceMode,
    EmployeeAssignmentBase,
    EmployeeAssignmentCreate,
    EmployeeAssignmentResponse,
    EmployeeBase,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeOffboard,
    EmployeeResponse,
    EmployeeUpdate,
)

__all__ = [
    "AttendanceMode",
    "EmployeeAssignmentBase",
    "EmployeeAssignmentCreate",
    "EmployeeAssignmentResponse",
    "EmployeeBase",
    "EmployeeCreate",
    "EmployeeListResponse",
    "EmployeeOffboard",
    "EmployeeResponse",
    "EmployeeUpdate",
]
