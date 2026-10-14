"""
app/schemas/employee.py

Request and response schemas for employee data management.
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.emergency_contact import EmergencyContactBase

# FIELD = absen di HP, OFFICE = absen di web
AttendanceMode = Literal["FIELD", "OFFICE"]


class EmployeeBase(BaseModel):
    """
    Base schema for an employee.
    """
    employee_no: str
    full_name: str
    position: str
    unit_id: UUID | None = None
    email: str | None = None
    phone: str | None = None
    join_date: date
    birth_date: date | None = None
    address: str | None = None
    photo_file_id: UUID | None = None


class EmployeeCreate(EmployeeBase):
    """
    Schema for creating a new employee.
    """
    attendance_mode: AttendanceMode = "FIELD"
    emergency_contacts: list[EmergencyContactBase] | None = None


class EmployeeUpdate(BaseModel):
    """
    Schema for updating employee details.
    """
    full_name: str | None = None
    attendance_mode: AttendanceMode | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    address: str | None = None
    photo_file_id: UUID | None = None


class EmployeeResponse(EmployeeBase):
    """
    Schema for an employee response object.
    """
    id: UUID
    attendance_mode: AttendanceMode = "FIELD"
    is_active: bool
    offboarded_at: datetime | None = None
    offboarding_reason: str | None = None


class EmployeeListResponse(BaseModel):
    """
    Schema for paginated employee lists.
    """
    items: list[EmployeeResponse]
    total: int
    page: int
    size: int


class EmployeeAssignmentBase(BaseModel):
    """
    Base schema for an employee assignment to a unit and position.
    """
    position: str
    unit_id: UUID | None = None
    valid_from: date


class EmployeeAssignmentCreate(EmployeeAssignmentBase):
    """
    Schema for assigning an employee.
    """


class EmployeeAssignmentResponse(EmployeeAssignmentBase):
    """
    Schema for responding with an employee assignment's details.
    """
    id: UUID
    employee_id: UUID
    valid_to: date | None = None
    unit_name: str | None = None


class EmployeeOffboard(BaseModel):
    """
    Schema for requesting to offboard an employee.
    """
    reason: str
