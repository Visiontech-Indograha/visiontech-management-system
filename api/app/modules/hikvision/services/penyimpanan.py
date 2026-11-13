"""Pembentukan baris `hikvision_event` dari `ParsedEvent`. Payload memakai daftar putih: tanpa gambar/biometrik."""
from __future__ import annotations

import hashlib
from typing import Any

from ..schemas.event import ParsedEvent


def kunci_event(device_serial: str, e: ParsedEvent) -> str:
    """Kunci cadangan (SHA-256 hex, 64 karakter) bila perangkat tidak mengirim nomor urut event."""
    mentah = "|".join([device_serial, str(e.major_event_type), str(e.minor_event_type), e.event_time.isoformat(),
                       e.employee_no_string or "", e.card_no or ""])
    return hashlib.sha256(mentah.encode()).hexdigest()


def baris_event(e: ParsedEvent) -> dict[str, Any]:
    return {
        "serial_no_event": e.serial_no_event,
        "event_key": None if e.serial_no_event is not None else kunci_event(e.device_serial, e),
        "major": e.major_event_type,
        "minor": e.minor_event_type,
        "event_time": e.event_time.isoformat(),
        "employee_no_string": e.employee_no_string,
        "card_no": e.card_no,
        "verify_mode": e.verify_mode,
        "payload": {
            "device_serial": e.device_serial,
            "serial_no_event": e.serial_no_event,
            "major": e.major_event_type,
            "minor": e.minor_event_type,
            "event_time": e.event_time.isoformat(),
            "employee_no_string": e.employee_no_string,
            "card_no": e.card_no,
            "verify_mode": e.verify_mode,
            "ada_gambar": e.ada_gambar,
        },
    }
