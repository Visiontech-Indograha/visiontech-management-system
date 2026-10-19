"""
app/schemas/emergency_contact.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.employees.schemas.employee_schema import (
    EmergencyContactBase,
    EmergencyContactCreate,
    EmergencyContactResponse,
    EmergencyContactUpdate,
)

__all__ = [
    "EmergencyContactBase",
    "EmergencyContactCreate",
    "EmergencyContactResponse",
    "EmergencyContactUpdate",
]
