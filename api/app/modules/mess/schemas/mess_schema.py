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
    address: str
    latitude: Decimal
    longitude: Decimal
    employee_id: UUID
    weekly_plan_id: UUID | None = None
    stay_start_date: date
    stay_end_date: date


class MessStayUpdate(BaseModel):
    mess_name: str | None = Field(None, min_length=2, max_length=150)
    city: str | None = Field(None, min_length=2, max_length=100)
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
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
    weekly_plan_id: UUID | None = None
    stay_start_date: date
    stay_end_date: date
    create_at: datetime
