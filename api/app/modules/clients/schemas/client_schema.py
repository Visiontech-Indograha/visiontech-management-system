"""Skema klien (tabel `client`) dan cabang/lokasi klien (tabel `client_sites`)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClientSiteOut(BaseModel):
    site_id: UUID
    client_id: UUID
    site_name: str
    address: str
    latitude: Decimal
    longitude: Decimal
    geofence_radius_meters: int = 100
    pic_name: str | None = None
    pic_phone: str | None = None


class ClientSiteCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    site_name: str = Field(min_length=2, max_length=150)
    address: str = Field(min_length=2, max_length=2000)
    latitude: Decimal = Field(ge=Decimal("-11.0"), le=Decimal("6.0"))
    longitude: Decimal = Field(ge=Decimal("95.0"), le=Decimal("141.0"))
    geofence_radius_meters: int = Field(default=100, ge=10, le=5000)
    pic_name: str | None = Field(None, max_length=120)
    pic_phone: str | None = Field(None, min_length=5, max_length=30, pattern=r"^[0-9+()\-\s]+$")


class ClientSiteUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    site_name: str | None = Field(None, min_length=2, max_length=150)
    address: str | None = Field(None, min_length=2, max_length=2000)
    latitude: Decimal | None = Field(None, ge=Decimal("-11.0"), le=Decimal("6.0"))
    longitude: Decimal | None = Field(None, ge=Decimal("95.0"), le=Decimal("141.0"))
    geofence_radius_meters: int | None = Field(None, ge=10, le=5000)
    pic_name: str | None = Field(None, max_length=120)
    pic_phone: str | None = Field(None, min_length=5, max_length=30, pattern=r"^[0-9+()\-\s]+$")


class ClientOut(BaseModel):
    client_id: UUID
    client_code: str
    name: str
    pic_name: str | None = None
    pic_phone: str | None = None
    address: str | None = None
    status: bool
    project_count: int = 0


class ClientWithSitesResponse(ClientOut):
    sites: list[ClientSiteOut] = Field(default_factory=list)


class ClientCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    client_code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=150)
    pic_name: str | None = Field(None, max_length=100)
    pic_phone: str | None = Field(None, min_length=5, max_length=30, pattern=r"^[0-9+()\-\s]+$")
    address: str | None = Field(None, max_length=2000)


class ClientUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    client_code: str | None = Field(None, min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(None, min_length=2, max_length=150)
    pic_name: str | None = Field(None, max_length=100)
    pic_phone: str | None = Field(None, min_length=5, max_length=30, pattern=r"^[0-9+()\-\s]+$")
    address: str | None = Field(None, max_length=2000)
    status: bool | None = None
