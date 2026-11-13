"""Skema admin perangkat Hikvision. Batas input sama dengan kolom tabel (hikvision_device / hikvision_employee_map).
Token penerima TIDAK pernah ada di skema baca; hanya `TokenBaru` yang memuatnya, sekali saat dibuat/diganti."""
from __future__ import annotations

import ipaddress
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

Mode = Literal["SHADOW", "AKTIF"]
_NO_PERANGKAT = r"^[A-Za-z0-9._-]{1,50}$"


def _ip(v: str) -> str:
    try:
        return str(ipaddress.ip_address(v.strip()))
    except ValueError as e:
        raise ValueError("Alamat IP tidak valid. Contoh: 192.168.1.50") from e


class PerangkatBuat(BaseModel):
    office_id: UUID
    name: str = Field(min_length=1, max_length=100)
    ip_address: str = Field(min_length=3, max_length=45)
    http_port: int = Field(80, ge=1, le=65535)
    serial_no: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    model: str | None = Field(None, max_length=64)
    mode: Mode = "SHADOW"
    aktif: bool = True
    catatan: str | None = Field(None, max_length=500)

    _cek_ip = field_validator("ip_address")(_ip)


class PerangkatUbah(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    ip_address: str | None = Field(None, min_length=3, max_length=45)
    http_port: int | None = Field(None, ge=1, le=65535)
    serial_no: str | None = Field(None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    model: str | None = Field(None, max_length=64)
    mode: Mode | None = None
    aktif: bool | None = None
    catatan: str | None = Field(None, max_length=500)

    @field_validator("ip_address")
    @classmethod
    def _cek_ip(cls, v: str | None) -> str | None:
        return None if v is None else _ip(v)


class PerangkatOut(BaseModel):
    device_id: UUID
    office_id: UUID
    office_name: str
    name: str
    ip_address: str
    http_port: int
    serial_no: str
    model: str | None
    mode: Mode
    aktif: bool
    catatan: str | None
    create_at: datetime
    update_at: datetime


class TokenBaru(BaseModel):
    """Ditampilkan SATU kali. Simpan sekarang; yang tersimpan di server hanya sidik jarinya."""

    device_id: UUID
    token: str
    receiver_url: str
    receiver_path: str


class PerangkatDibuat(BaseModel):
    perangkat: PerangkatOut
    penerima: TokenBaru


class PemetaanBuat(BaseModel):
    employee_no_string: str = Field(pattern=_NO_PERANGKAT, description="Nomor karyawan di perangkat")
    employee_id: UUID


class PemetaanUbah(BaseModel):
    employee_id: UUID


class PemetaanOut(BaseModel):
    map_id: UUID
    device_id: UUID
    employee_no_string: str
    employee_id: UUID
    employee_no: str
    full_name: str
    create_at: datetime


class PemetaanDiterapkan(BaseModel):
    event_diperbarui: int
    masih_ada_sisa: bool = Field(description="True bila masih ada event lain; jalankan lagi")


class UsulanCocok(BaseModel):
    employee_no_string: str
    employee_id: UUID
    employee_no: str
    full_name: str
    jumlah_event: int


class UsulanTakCocok(BaseModel):
    employee_no_string: str
    jumlah_event: int
    alasan: str


class UsulanPemetaan(BaseModel):
    cocok: list[UsulanCocok]
    tidak_cocok: list[UsulanTakCocok]


class PemetaanOtomatisOut(BaseModel):
    dibuat: int
    event_diperbarui: int
    masih_ada_sisa: bool
    tidak_cocok: list[UsulanTakCocok]


class StatusPerangkat(BaseModel):
    device_id: UUID
    mode: Mode
    aktif: bool
    event_24_jam: int
    event_7_hari: int
    event_terakhir_diterima: datetime | None
    belum_terpetakan_7_hari: int
    kemungkinan_duplikat_7_hari: int = Field(
        description="Kelompok event dengan nomor, waktu, dan jenis sama (duplikat murni ditolak penyimpanan)"
    )


class BandingBaris(BaseModel):
    employee_id: UUID
    employee_name: str
    tgl: date
    pertama: datetime
    terakhir: datetime
    jumlah: int
    clock_in_at: datetime | None
    clock_out_at: datetime | None
    selisih_masuk_menit: int | None
    selisih_pulang_menit: int | None


class BandingBayangan(BaseModel):
    """Pembanding mode bayangan (baca saja): tap mesin vs absen aplikasi per karyawan-hari."""
    device_id: UUID
    mode: Mode
    dari: date
    sampai: date
    akan_menghasilkan_absen: int
    total_karyawan_hari: int
    tak_terpetakan: int
    terpotong: bool
    items: list[BandingBaris]
