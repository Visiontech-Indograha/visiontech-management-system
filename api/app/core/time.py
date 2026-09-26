"""
app/core/time.py
Sumber tunggal waktu server.
JANGAN gunakan datetime.now() atau datetime.utcnow() di mana pun selain file ini.
Lihat docs/12-STANDAR-BACKEND.md — "Waktu | Hanya lewat core/time.py".
"""
from datetime import UTC, datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7), "WIB")  # Indonesia tanpa DST; tak butuh tzdata di image slim


def utcnow() -> datetime:
    """Waktu saat ini dalam UTC, timezone-aware. Pakai ini, bukan datetime.now()."""
    return datetime.now(tz=UTC)


def jakarta_now() -> datetime:
    """Waktu saat ini di zona Asia/Jakarta (UTC+7) — hanya untuk tampilan/log."""
    from zoneinfo import ZoneInfo
    return datetime.now(tz=ZoneInfo("Asia/Jakarta"))


def wib_text(value: datetime | str | None) -> str:
    """Format tampilan dokumen: `26-09-2026 17:41 WIB` (nilai tanpa zona dianggap UTC)."""
    if not value:
        return ""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return f"{value.astimezone(WIB):%d-%m-%Y %H:%M} WIB"
