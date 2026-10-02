from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class EmployeeBase(BaseModel):
    employee_no: str
    full_name: str
    position: str
    unit_id: UUID | None = None
    email: str | None = None
    phone: str | None = None
    join_date: date
    birth_date: date | None = None
    address: str | None = None
    emergency_contact: str | None = None

class EmployeeCreate(EmployeeBase):
    pass

AttendanceMode = Literal["FIELD", "OFFICE"]  # FIELD = absen di HP, OFFICE = absen di web


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    attendance_mode: AttendanceMode | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    address: str | None = None
    emergency_contact: str | None = None

class EmployeeResponse(EmployeeBase):
    id: UUID
    attendance_mode: AttendanceMode = "FIELD"
    is_active: bool
    offboarded_at: datetime | None = None
    offboarding_reason: str | None = None
    
class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int
    page: int
    size: int

class EmployeeAssignmentBase(BaseModel):
    position: str
    unit_id: UUID | None = None
    valid_from: date

class EmployeeAssignmentCreate(EmployeeAssignmentBase):
    pass

class EmployeeAssignmentResponse(EmployeeAssignmentBase):
    id: UUID
    employee_id: UUID
    valid_to: date | None = None
    unit_name: str | None = None

class EmployeeOffboard(BaseModel):
    reason: str
