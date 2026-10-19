"""Skema jenis pekerjaan + template foto laporan + metadata bukti foto (Rencana Kerja v3, T9)."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

EvidenceSource = Literal["CAMERA", "GALLERY"]


class WorkTypePhotoIn(BaseModel):
    """Satu slot foto pada template: label, petunjuk, wajib/tidak."""
    label: str = Field(..., min_length=1, max_length=80)  # Nama slot, mis. "Foto panel sebelum"
    hint: str | None = Field(None, max_length=300)  # Petunjuk pengambilan foto
    required: bool = False  # Wajib terisi sebelum laporan dikirim
    example_file_id: str | None = None  # Foto contoh dari PM (berkas yang sudah diunggah atau path)


class WorkTypePhotoOut(BaseModel):
    """Slot foto pada template (keluaran)."""
    id: UUID  # ID slot
    sort_order: int  # Urutan tampil
    label: str  # Nama slot
    hint: str | None = None  # Petunjuk
    required: bool = False  # Wajib
    example_file_id: str | None = None  # Foto contoh dari PM (None = tanpa contoh atau path)


class WorkTypeIn(BaseModel):
    """Membuat/mengubah jenis pekerjaan; `photos` mengganti seluruh daftar slot."""
    name: str = Field(..., min_length=1, max_length=100)  # Nama jenis, mis. "Replacement"
    division_id: UUID | None = None  # ID Divisi pemilik work type
    description: str | None = Field(None, max_length=255)  # Keterangan pekerjaan
    photos: list[WorkTypePhotoIn] = []  # Template foto, urut sesuai daftar


class WorkTypeOut(BaseModel):
    """Jenis pekerjaan beserta template fotonya."""
    id: UUID  # ID jenis
    division_id: UUID | None = None  # ID Divisi pemilik
    division_name: str | None = None  # Nama Divisi
    name: str  # Nama jenis
    description: str | None = None  # Keterangan pekerjaan
    is_active: bool = True  # Nonaktif = tidak ditawarkan lagi, rencana kerja lama tetap utuh
    photos: list[WorkTypePhotoOut] = []  # Template foto


class EvidenceIn(BaseModel):
    """Foto bukti laporan: file + slot template yang dipenuhi + sumbernya."""
    file_id: UUID  # ID berkas yang sudah diunggah
    slot_label: str | None = Field(None, max_length=80)  # Slot template (kosong = "Foto lain")
    source: EvidenceSource = "CAMERA"  # CAMERA = kamera aplikasi bertanda air; GALLERY = dari galeri


class EvidenceOut(BaseModel):
    """Foto bukti laporan (keluaran)."""
    file_id: UUID  # ID berkas
    slot_label: str | None = None  # Slot template
    source: EvidenceSource = "CAMERA"  # Sumber foto


def merge_evidence(file_ids: list[UUID], evidence: list[EvidenceIn]) -> list[tuple[str, str | None, str]]:
    """Gabung daftar id lama (APK lama) dan daftar berlabel: (file_id, slot_label, source) tanpa duplikat."""
    merged: dict[str, tuple[str, str | None, str]] = {}
    for e in evidence:
        merged[str(e.file_id)] = (str(e.file_id), (e.slot_label or "").strip() or None, e.source)
    for f in file_ids:
        merged.setdefault(str(f), (str(f), None, "CAMERA"))
    return list(merged.values())
