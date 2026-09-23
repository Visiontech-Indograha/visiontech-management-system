"""
app/core/time.py
Sumber tunggal waktu server.
JANGAN gunakan datetime.now() atau datetime.utcnow() di mana pun selain file ini.
Lihat docs/12-STANDAR-BACKEND.md — "Waktu | Hanya lewat core/time.py".
"""
from datetime import UTC, datetime


def utcnow() -> datetime:
    """Waktu saat ini dalam UTC, timezone-aware. Pakai ini, bukan datetime.now()."""
    return datetime.now(tz=UTC)


def jakarta_now() -> datetime:
    """Waktu saat ini di zona Asia/Jakarta (UTC+7) — hanya untuk tampilan/log."""
    from zoneinfo import ZoneInfo
    return datetime.now(tz=ZoneInfo("Asia/Jakarta"))
