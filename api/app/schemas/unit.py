"""Skema permintaan & respons: unit (dipindah dari api/v1/endpoints/units.py, R-28 M2b)."""
from uuid import UUID

from pydantic import BaseModel


class UnitOut(BaseModel):
    id: UUID
    code: str
    name: str
