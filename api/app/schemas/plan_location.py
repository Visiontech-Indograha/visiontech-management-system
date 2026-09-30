"""Skema permintaan & respons: plan location (dipindah dari api/v1/endpoints/work_plan_location.py, R-28 M2b)."""
from uuid import UUID

from pydantic import BaseModel, Field


class GeoResult(BaseModel):
    name: str
    lat: float
    lng: float
    type: str


class PlanLocationIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_m: int = 100


class PlanLocationOut(BaseModel):
    id: UUID
    name: str
    address: str | None
    lat: float
    lng: float
    radius_m: int | None
