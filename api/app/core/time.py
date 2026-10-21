"""
app/core/time.py
Sumber tunggal waktu server.
JANGAN gunakan datetime.now() atau datetime.utcnow() di mana pun selain file ini.
Lihat docs/12-STANDAR-BACKEND.md — "Waktu | Hanya lewat core/time.py".
"""
from datetime import UTC, date, datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7), "WIB")  # Indonesia tanpa DST; tak butuh tzdata di image slim

# Jam simulasi KHUSUS pengembangan (uji skenario beberapa minggu dalam satu hari). Hanya menggeser tanggal bisnis
# (`jakarta_now`); `utcnow` (token, sesi, audit) tetap waktu nyata. Diatur lewat PUT /system/dev-clock, yang
# ditolak bila APP_ENV=production. Proses dimulai ulang → kembali ke waktu nyata.
_dev_offset = timedelta(0)


def set_dev_today(target: date | None) -> date:
    """Geser tanggal bisnis ke `target` (None = waktu nyata); mengembalikan tanggal bisnis yang berlaku."""
    global _dev_offset
    _dev_offset = timedelta(0)
    if target is not None:
        _dev_offset = timedelta(days=(target - jakarta_now().date()).days)
    return jakarta_now().date()


def utcnow() -> datetime:
    """Waktu saat ini dalam UTC, timezone-aware. Pakai ini, bukan datetime.now()."""
    return datetime.now(tz=UTC)


def jakarta_now() -> datetime:
    """Waktu saat ini di zona Asia/Jakarta (UTC+7) — hanya untuk tampilan/log."""
    from zoneinfo import ZoneInfo
    return datetime.now(tz=ZoneInfo("Asia/Jakarta")) + _dev_offset


def wib_text(value: datetime | str | None) -> str:
    """Format tampilan dokumen: `26-09-2026 17:41 WIB` (nilai tanpa zona dianggap UTC)."""
    if not value:
        return ""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return f"{value.astimezone(WIB):%d-%m-%Y %H:%M} WIB"
