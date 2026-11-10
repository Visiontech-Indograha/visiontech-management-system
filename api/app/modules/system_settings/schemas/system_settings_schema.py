"""Skema setelan sistem. Hanya tipe boolean saat ini."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, StrictBool


class SystemSettingOut(BaseModel):
    key: str
    label: str
    description: str
    type: Literal["bool"] = "bool"
    value: bool  # nilai efektif sekarang
    source: Literal["env_force", "db", "env_default"]  # asal nilai efektif
    env_default: bool  # nilai bawaan dari env (dipakai bila tidak ada baris di tabel)
    locked: bool  # true = dikunci env SYSTEM_SETTINGS_FORCE, tidak bisa diubah lewat API
    updated_at: datetime | None = None


class SystemSettingsUpdate(BaseModel):
    """Kunci = nama setelan (lihat GET). Nilai harus boolean sungguhan (bukan teks/angka)."""

    values: dict[str, StrictBool] = Field(min_length=1, max_length=20)
