"""
app/modules/mess/schemas/mess_schema.py
Skema data Pydantic untuk Mess Karyawan (company_mess_stay).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class MessStayCreate(BaseModel):
    mess_name: str = Field(..., min_length=2, max_length=150)
    city: str = Field(..., min_length=2, max_length=100)
    address: str = Field(min_length=3, max_length=500)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    employee_id: UUID
    stay_start_date: date
    stay_end_date: date


class MessStayUpdate(BaseModel):
    mess_name: str | None = Field(None, min_length=2, max_length=150)
    city: str | None = Field(None, min_length=2, max_length=100)
    address: str | None = Field(None, min_length=3, max_length=500)
    latitude: Decimal | None = Field(None, ge=-90, le=90)
    longitude: Decimal | None = Field(None, ge=-180, le=180)
    stay_start_date: date | None = None
    stay_end_date: date | None = None


class MessStayOut(BaseModel):
    mess_stay_id: UUID
    mess_name: str
    city: str
    address: str
    latitude: Decimal
    longitude: Decimal
    employee_id: UUID
    employee_name: str | None = None
    employee_no: str | None = None
    stay_start_date: date
    stay_end_date: date
    create_at: datetime
