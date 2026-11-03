"""
app/shared/attendance_sql.py
Potongan SQL bersama untuk aturan jam absensi: terlambat = absen masuk (jam WIB) lewat batas
`ATTENDANCE_LATE_AFTER` (bawaan 08:00), bukan lagi jam masuk kantor.
"""
from __future__ import annotations

from app.core.config import settings

IS_LATE = f"(clock_in_at AT TIME ZONE 'Asia/Jakarta')::time > TIME '{settings.ATTENDANCE_LATE_AFTER}'"
IS_LATE_A = IS_LATE.replace("(clock_in_at", "(a.clock_in_at", 1)

# Zona luar kota efektif: absensi di luar batas kota kantor utama ATAU karyawan ditugaskan pada jadwal luar kota.
EFFECTIVE_CITY_ZONE_A = """(CASE WHEN a.city_zone_status = 'LUAR_KOTA' OR EXISTS (
    SELECT 1 FROM work_plan_daily wpd_oz JOIN team t_oz ON t_oz.team_id = wpd_oz.team_id
    WHERE wpd_oz.work_date = a.attendance_date AND wpd_oz.is_out_of_town = TRUE
      AND wpd_oz.status IN ('APPROVED', 'ONGOING', 'COMPLETED') AND wpd_oz.delete_at IS NULL
      AND (t_oz.leader_employee_id = a.employee_id OR EXISTS (
          SELECT 1 FROM member m_oz WHERE m_oz.team_id = wpd_oz.team_id
            AND m_oz.employee_id = a.employee_id AND m_oz.is_active AND m_oz.delete_at IS NULL))
) THEN 'LUAR_KOTA' ELSE 'DALAM_KOTA' END)"""

EFFECTIVE_MEAL_AMOUNT_A = f"""(CASE WHEN {EFFECTIVE_CITY_ZONE_A} = 'LUAR_KOTA' THEN GREATEST(
    a.meal_allowance_amount,
    COALESCE(
        (SELECT o_m.out_city_meal_rate FROM office o_m
         WHERE o_m.is_main_office = TRUE AND o_m.delete_at IS NULL LIMIT 1),
        a.meal_allowance_amount
    )
) ELSE a.meal_allowance_amount END)"""
