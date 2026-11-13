from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PullCursor:
    """Posisi lanjut tarik riwayat: jendela yang sedang dibaca dan posisi hasil di dalamnya."""
    window_start: datetime
    position: int = 0
    selesai: bool = False


@dataclass(frozen=True, slots=True)
class DryRunResult:
    total_event: int
    event_tertua: datetime | None
    jendela_diperiksa: int
    jumlah_permintaan: int
