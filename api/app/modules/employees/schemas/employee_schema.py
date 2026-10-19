"""
app/modules/employees/schemas/employee_schema.py

Request and response schemas for employee data management, emergency contacts, and assignments.
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# FIELD = absen di HP, OFFICE = absen di web
AttendanceMode = Literal["FIELD", "OFFICE"]


class EmergencyContactBase(BaseModel):
    """Base schema for an employee emergency contact."""
    name: str = Field(..., min_length=1, max_length=150)
    relationship: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=1, max_length=50)
    address: str | None = None
    is_primary: bool = True


class EmergencyContactCreate(EmergencyContactBase):
    """Schema for adding a new emergency contact."""


class EmergencyContactUpdate(BaseModel):
    """Schema for updating an existing emergency contact."""
    name: str | None = Field(None, min_length=1, max_length=150)
    relationship: str | None = Field(None, min_length=1, max_length=50)
    phone: str | None = Field(None, min_length=1, max_length=50)
    address: str | None = None
    is_primary: bool | None = None


class EmergencyContactResponse(EmergencyContactBase):
    """Schema for returning an emergency contact response."""
    id: UUID
    employee_id: UUID
    created_at: datetime
    updated_at: datetime


class EmployeeBase(BaseModel):
    """Base schema for an employee."""
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
    """Schema for creating a new employee."""
    attendance_mode: AttendanceMode = "FIELD"
    emergency_contacts: list[EmergencyContactBase] | None = None


class EmployeeUpdate(BaseModel):
    """Schema for updating employee details."""
    full_name: str | None = None
    attendance_mode: AttendanceMode | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    address: str | None = None
    photo_file_id: UUID | None = None
    is_active: bool | None = None


class EmployeeResponse(EmployeeBase):
    """Schema for an employee response object."""
    id: UUID
    attendance_mode: AttendanceMode = "FIELD"
    is_active: bool
    offboarded_at: datetime | None = None
    offboarding_reason: str | None = None
    user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    emergency_contacts: list[EmergencyContactResponse] = []

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    """Schema for paginated employee lists."""
    items: list[EmployeeResponse]
    total: int
    page: int = 1
    size: int = 50


class EmployeeAssignmentBase(BaseModel):
    """Base schema for an employee assignment to a unit and position."""
    position: str
    unit_id: UUID | None = None
    valid_from: date


class EmployeeAssignmentCreate(EmployeeAssignmentBase):
    """Schema for assigning an employee."""


class EmployeeAssignmentResponse(EmployeeAssignmentBase):
    """Schema for responding with an employee assignment's details."""
    id: UUID
    employee_id: UUID
    valid_to: date | None = None
    unit_name: str | None = None


class EmployeeOffboard(BaseModel):
    """Schema for requesting to offboard an employee."""
    reason: str


__all__ = [
    "AttendanceMode",
    "EmergencyContactBase",
    "EmergencyContactCreate",
    "EmergencyContactResponse",
    "EmergencyContactUpdate",
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
