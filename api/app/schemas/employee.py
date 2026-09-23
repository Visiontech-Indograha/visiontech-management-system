from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID

class EmployeeBase(BaseModel):
    employee_no: str
    full_name: str
    position: str
    unit_id: Optional[UUID] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    join_date: date
    birth_date: Optional[date] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

class EmployeeResponse(EmployeeBase):
    id: UUID
    is_active: bool
    offboarded_at: Optional[datetime] = None
    offboarding_reason: Optional[str] = None
    
class EmployeeListResponse(BaseModel):
    items: List[EmployeeResponse]
    total: int
    page: int
    size: int

class EmployeeAssignmentBase(BaseModel):
    position: str
    unit_id: Optional[UUID] = None
    valid_from: date

class EmployeeAssignmentCreate(EmployeeAssignmentBase):
    pass

class EmployeeAssignmentResponse(EmployeeAssignmentBase):
    id: UUID
    employee_id: UUID
    valid_to: Optional[date] = None

class EmployeeOffboard(BaseModel):
    reason: str
