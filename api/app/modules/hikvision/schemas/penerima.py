from __future__ import annotations

from pydantic import BaseModel


class PenerimaOut(BaseModel):
    """Jawaban singkat ke perangkat. Tanpa data pribadi."""

    status: str  # diterima | duplikat | diabaikan
    kode: str
