"""Paket skema modul employees."""

from app.modules.employees.schemas.employee_schema import (
    AddressIn,
    AddressOut,
    EmployeeCreate,
    EmployeeDetail,
    EmployeeListResponse,
    EmployeeOut,
    EmployeeUpdate,
)

__all__ = ["AddressIn", "AddressOut", "EmployeeCreate", "EmployeeDetail", "EmployeeListResponse", "EmployeeOut",
           "EmployeeUpdate"]
