"""Skema jenis pekerjaan + template foto laporan + metadata bukti foto (Rencana Kerja v3, T9)."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

EvidenceSource = Literal["CAMERA", "GALLERY"]
# WORK = pekerjaan biasa; SURVEY_TASK = paket survei di jadwal; SURVEY_POINT = jenis titik survei (docs/37 §9)
WorkTypeKind = Literal[
    "WORK",
    "INSTALLATION",
    "SURVEY_TASK",
    "SURVEY_POINT",
    "MAINTENANCE",
    "REPLACEMENT",
    "PREPARATION",
    "DISMANTLE",
    "COMMISSIONING",
    "TROUBLESHOOTING",
]


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


class DefaultMaterialIn(BaseModel):
    """Schema input template material default untuk jenis pekerjaan."""
    material_code: str | None = Field(None, max_length=50)
    material_name: str = Field(..., min_length=1, max_length=255)
    default_qty: float = Field(default=1.0, ge=0.0)
    unit: str = Field(default="Unit", max_length=50)
    category: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=2000)
    sort_order: int = 0


class DefaultMaterialUpdate(BaseModel):
    """Schema perbaikan template material default."""
    material_code: str | None = Field(None, max_length=50)
    material_name: str | None = Field(None, min_length=1, max_length=255)
    default_qty: float | None = Field(None, ge=0.0)
    unit: str | None = Field(None, max_length=50)
    category: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=2000)
    sort_order: int | None = None


class DefaultMaterialOut(BaseModel):
    """Schema output template material default jenis pekerjaan."""
    default_material_id: UUID
    work_type_id: UUID
    material_code: str | None = None
    material_name: str
    default_qty: float
    unit: str
    category: str | None = None
    description: str | None = None
    sort_order: int = 0


class WorkTypeIn(BaseModel):
    """Membuat/mengubah jenis pekerjaan; `photos` mengganti seluruh daftar slot."""
    name: str = Field(..., min_length=1, max_length=100)  # Nama jenis, mis. "Replacement"
    division_id: UUID | None = None  # ID Divisi pemilik work type
    description: str | None = Field(None, max_length=255)  # Keterangan pekerjaan
    photos: list[WorkTypePhotoIn] = []  # Template foto, urut sesuai daftar
    kind: WorkTypeKind = "WORK"
    follow_up_work_type_id: UUID | None = None  # SURVEY_POINT → jenis pekerjaan pemasangannya (rencana dari survei)


class WorkTypeOut(BaseModel):
    """Jenis pekerjaan beserta template foto dan template material default."""
    id: UUID  # ID jenis
    division_id: UUID | None = None  # ID Divisi pemilik
    division_name: str | None = None  # Nama Divisi
    name: str  # Nama jenis
    description: str | None = None  # Keterangan pekerjaan
    is_active: bool = True  # Nonaktif = tidak ditawarkan lagi, rencana kerja lama tetap utuh
    kind: WorkTypeKind = "WORK"
    follow_up_work_type_id: UUID | None = None
    follow_up_name: str | None = None
    photos: list[WorkTypePhotoOut] = []  # Template foto
    default_materials: list[DefaultMaterialOut] = []  # Template material default BoM


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
