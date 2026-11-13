"""Model terstandar event perangkat Hikvision. Tidak pernah memuat gambar, embedding, atau templat wajah."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ParseStatus(StrEnum):
    OK = "OK"                  # event verifikasi lolos, siap diolah
    DIABAIKAN = "DIABAIKAN"    # sah tetapi bukan verifikasi lolos (heartbeat, wajah tak dikenal, pintu, dll.)
    DITOLAK = "DITOLAK"        # kiriman rusak/berbahaya/tidak masuk akal


@dataclass(frozen=True, slots=True)
class ParsedEvent:
    device_serial: str
    serial_no_event: int | None
    major_event_type: int
    minor_event_type: int
    event_time: datetime          # selalu beroffset (aware)
    employee_no_string: str | None
    card_no: str | None
    verify_mode: str | None
    ada_gambar: bool              # hanya penanda; byte gambar tidak ikut model ini


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    status: ParseStatus
    kode: str                     # kode stabil: OK, HEARTBEAT, BUKAN_VERIFIKASI, TERLALU_BESAR, FORMAT_RUSAK, ...
    pesan: str                    # kalimat Indonesia awam, aman ditampilkan
    event: ParsedEvent | None = None
    gambar: bytes | None = None   # JPEG tervalidasi; pemanggil memutuskan disimpan atau tidak (default: tidak)
    catatan: list[str] = field(default_factory=list)  # mis. gambar ditolak tetapi event tetap diolah
