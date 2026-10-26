"""
app/shared/attendance_sql.py
Potongan SQL bersama untuk aturan jam absensi: terlambat = absen masuk (jam WIB) lewat batas
`ATTENDANCE_LATE_AFTER` (bawaan 08:00), bukan lagi jam masuk kantor.
"""
from __future__ import annotations

from app.core.config import settings

IS_LATE = f"(clock_in_at AT TIME ZONE 'Asia/Jakarta')::time > TIME '{settings.ATTENDANCE_LATE_AFTER}'"
IS_LATE_A = IS_LATE.replace("(clock_in_at", "(a.clock_in_at", 1)
