from datetime import date, datetime
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

class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    address: str | None = None
    emergency_contact: str | None = None

class EmployeeResponse(EmployeeBase):
    id: UUID
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

class EmployeeOffboard(BaseModel):
    reason: str
