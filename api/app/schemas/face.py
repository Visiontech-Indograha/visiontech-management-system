"""
app/schemas/face.py

Skema pengenalan wajah untuk absensi HP: persetujuan biometrik, pendaftaran, template di HP, dan gambar wajah
sementara (probe). Embedding tidak pernah masuk log; template hanya dikembalikan ke pemiliknya.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ConsentState = Literal["GRANTED", "WITHDRAWN"]


class FaceLiveness(BaseModel):
    """Hasil tantangan keaslian wajah (anti foto layar) dari HP: dua tantangan acak."""
    challenges: list[str] = Field(default_factory=list, max_length=6)
    passed: bool = False
    # Bukti dari POST /face/challenge-check (satu per tantangan lolos). Hanya ini yang dipercaya untuk absen ONLINE;
    # `passed` adalah klaim HP dan hanya berlaku untuk absen luring (tidak ada server saat itu).
    proofs: list[str] = Field(default_factory=list, max_length=6)


class FacePolicy(BaseModel):
    """Teks persetujuan biometrik milik server (klien tidak bisa mengubah kalimat yang disetujui)."""
    version: str
    text: str


class FaceStatus(BaseModel):
    employee_linked: bool
    consent: ConsentState | None = None          # None = belum pernah memilih
    consent_policy_version: str | None = None
    enrolled: bool = False
    enrollment_version: str | None = None        # berubah setiap pendaftaran ulang; HP memakainya untuk memperbarui template
    model_name: str | None = None
    model_version: str | None = None
    liveness_required: bool = True
    template_ttl_days: int
    policy: FacePolicy


class ConsentRequest(BaseModel):
    state: ConsentState
    # Wajib sama dengan versi kebijakan server saat ini (mencegah menyetujui teks yang sudah usang).
    policy_version: str = Field(..., min_length=1, max_length=40)


class EnrollResponse(BaseModel):
    enrolled: int                                 # jumlah pose yang tersimpan
    enrollment_version: str
    model_name: str
    model_version: str


class TemplateResponse(BaseModel):
    """Embedding MILIK SENDIRI untuk dicocokkan di HP saat luring. Disimpan terenkripsi (Keystore); berlaku terbatas."""
    model_name: str
    model_version: str
    enrollment_version: str
    embeddings: list[list[float]]
    expires_at: datetime


class ProbeResponse(BaseModel):
    probe_id: UUID
    quality: float | None = None
    # True = face-service sedang tidak tersedia; gambar disimpan dan diperiksa ulang nanti (absen tetap bisa).
    pending: bool = False
    expires_at: datetime


class ChallengeCheckResponse(BaseModel):
    status: Literal["sukses", "menunggu"]
    detail: str
    quality: float | None = None
    # Bukti bertanda tangan server; hanya ada bila status "sukses". Kirim kembali di `liveness.proofs`.
    proof: str | None = None
