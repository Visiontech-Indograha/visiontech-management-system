"""Skema rilis aplikasi Android dan pemeriksaan pembaruan (docs/32)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

UpdateStatus = Literal["UP_TO_DATE", "OPTIONAL", "REQUIRED"]

# Nama berkas APK berversi; juga satu-satunya bentuk nama yang boleh dilayani (tanpa garis miring / "..").
APK_NAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._+-]*\.apk$"


class ReleaseFile(BaseModel):
    """Satu APK di manifest `latest.json` untuk satu arsitektur CPU."""

    abi: str = Field(min_length=1, max_length=32)          # arm64-v8a, armeabi-v7a, x86_64
    name: str = Field(pattern=APK_NAME_PATTERN, max_length=120)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(gt=0)                                # bita


class ReleaseManifest(BaseModel):
    """Isi `android/latest.json` yang ditulis skrip `scripts/rilis-apk.sh`."""

    package: str = "com.visiontech.vms_mobile"
    version_name: str = Field(min_length=1, max_length=32)
    build: int = Field(ge=1)                               # versionCode Android
    min_build: int = Field(default=1, ge=1)                # build di bawah ini wajib memperbarui
    released_at: datetime
    notes: list[str] = []
    files: list[ReleaseFile] = Field(min_length=1)


class ReleaseFileOut(BaseModel):
    """Berkas yang cocok untuk HP penanya."""

    abi: str
    url: str                                               # jalur relatif ke host API, bukan URL lain
    sha256: str
    size: int


class AppUpdateOut(BaseModel):
    """Jawaban pemeriksaan pembaruan untuk satu HP."""

    status: UpdateStatus
    current_build: int
    latest_build: int | None = None
    latest_version: str | None = None
    min_build: int | None = None
    released_at: datetime | None = None
    notes: list[str] = []
    download: ReleaseFileOut | None = None
