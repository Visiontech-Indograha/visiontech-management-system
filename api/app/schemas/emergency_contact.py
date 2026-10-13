"""
app/schemas/emergency_contact.py

Request and response schemas for employee emergency contacts.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EmergencyContactBase(BaseModel):
    """
    Base schema for an employee emergency contact.
    """
    name: str = Field(..., min_length=1, max_length=150)
    relationship: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=1, max_length=50)
    address: str | None = None
    is_primary: bool = True


class EmergencyContactCreate(EmergencyContactBase):
    """
    Schema for adding a new emergency contact.
    """


class EmergencyContactUpdate(BaseModel):
    """
    Schema for updating an existing emergency contact.
    """
    name: str | None = Field(None, min_length=1, max_length=150)
    relationship: str | None = Field(None, min_length=1, max_length=50)
    phone: str | None = Field(None, min_length=1, max_length=50)
    address: str | None = None
    is_primary: bool | None = None


class EmergencyContactResponse(EmergencyContactBase):
    """
    Schema for returning an emergency contact response.
    """
    id: UUID
    employee_id: UUID
    created_at: datetime
    updated_at: datetime
