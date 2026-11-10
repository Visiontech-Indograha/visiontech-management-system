"""Skema penyiapan awal. Batas input sama dengan form web (SetupPage)."""
from __future__ import annotations

from pydantic import BaseModel, Field

PASSWORD_MIN = 12
PASSWORD_MAX = 128


class SetupStatusOut(BaseModel):
    needs_setup: bool  # true = belum ada SUPER_ADMIN aktif
    enabled: bool  # true = server punya SETUP_TOKEN valid (kalau false, minta operator mengisinya)


class SetupAdminIn(BaseModel):
    setup_token: str = Field(min_length=1, max_length=200)
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class SetupAdminOut(BaseModel):
    user_id: str
    email: str
