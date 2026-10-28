"""Skema klien (tabel `client`)."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ClientOut(BaseModel):
    client_id: UUID
    client_code: str
    name: str
    pic_name: str | None = None
    pic_phone: str | None = None
    address: str | None = None
    status: bool
    project_count: int = 0


class ClientCreate(BaseModel):
    client_code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=150)
    pic_name: str | None = Field(None, max_length=100)
    pic_phone: str | None = Field(None, min_length=5, max_length=30, pattern=r"^[0-9+()\-\s]+$")
    address: str | None = Field(None, max_length=2000)


class ClientUpdate(BaseModel):
    client_code: str | None = Field(None, min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(None, min_length=2, max_length=150)
    pic_name: str | None = Field(None, max_length=100)
    pic_phone: str | None = Field(None, min_length=5, max_length=30, pattern=r"^[0-9+()\-\s]+$")
    address: str | None = Field(None, max_length=2000)
    status: bool | None = None
