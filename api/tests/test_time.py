"""core/time.py — sumber tunggal waktu server; WIB harus tersedia di semua platform (paket tzdata)."""
from datetime import timedelta

from app.core.time import jakarta_now, utcnow


def test_jakarta_now_is_utc_plus_seven():
    assert jakarta_now().utcoffset() == timedelta(hours=7)


def test_utcnow_is_timezone_aware_utc():
    assert utcnow().utcoffset() == timedelta(0)
