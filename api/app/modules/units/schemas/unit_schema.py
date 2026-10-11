"""
app/modules/units/schemas/unit_schema.py

Skema data keluaran unit organisasi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.5.
"""
from uuid import UUID

from pydantic import BaseModel


class UnitOut(BaseModel):
    """
    Skema data representasi unit kerja organisasi.
    """
    id: UUID
    code: str
    name: str

