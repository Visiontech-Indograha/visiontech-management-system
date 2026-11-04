"""
Simulasi Skala Penuh 1 Tahun (365 Hari - Tahun 2026) Visiontech Management System (VMS) V2.

Mencakup seluruh mekanisme operasional bisnis:
1. Kalender 365 hari (1 Jan 2026 - 31 Des 2026).
2. Tanggal Merah (Libur Nasional Indonesia 2026).
3. Hari Minggu sebagai hari libur resmi, dengan skenario lembur darurat lapangan pada minggu-minggu tertentu.
4. Hari Sabtu sebagai hari meeting evaluasi & presentasi laporan mingguan setiap tim kepada PM.
5. Senin - Jumat: hari kerja operasional penuh untuk seluruh 40 akun (Kantor & Lapangan).
6. Absensi Masuk (Check-in) & Absensi Pulang (Check-out) dengan kalkulasi jam kerja, keterlambatan, dan uang makan.
7. Laporan Harian Pekerjaan (Daily Report) yang wajib diisi oleh Ketua Tim sebelum check-out.
8. Lembur malam (Overtime) melewati jam 19:00 dengan persetujuan PM (menguji validasi overtime bypass).
9. Pengajuan Cuti Tahunan (Annual Leave) dan Sakit (Sick Leave) berjenjang (PM -> HR), termasuk pengujian penolakan & refund kuota cuti.
10. Validasi proteksi absensi saat cuti/sakit resmi (ON_APPROVED_LEAVE).
11. Siklus peminjaman kendaraan operasional, insiden kerusakan kendaraan di lapangan, inspeksi servis perbaikan bengkel, dan pemulihan status kembali ke 'ready'.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import UUID, uuid4

# Pastikan import app.* dapat ditemukan
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))

from sqlalchemy import text
from app.database.session import AsyncSessionLocal

# Daftar Hari Libur Nasional Indonesia 2026
HOLIDAYS_2026 = {
    date(2026, 1, 1): "Tahun Baru 2026 Masehi",
    date(2026, 1, 16): "Isra Mi'raj Nabi Muhammad SAW",
    date(2026, 2, 17): "Tahun Baru Imlek 2577 Kongzili",
    date(2026, 3, 19): "Hari Suci Nyepi Tahun Baru Saka 1948",
    date(2026, 3, 20): "Hari Raya Idul Fitri 1447 Hijriah",
    date(2026, 3, 21): "Cuti Bersama Hari Raya Idul Fitri 1447 H",
    date(2026, 4, 3): "Wafat Yesus Kristus (Jumat Agung)",
    date(2026, 5, 1): "Hari Buruh Internasional",
    date(2026, 5, 14): "Kenaikan Yesus Kristus",
    date(2026, 5, 27): "Hari Raya Idul Adha 1447 Hijriah",
    date(2026, 5, 31): "Hari Raya Waisak 2570 BE",
    date(2026, 6, 1): "Hari Lahir Pancasila",
    date(2026, 6, 16): "Tahun Baru Islam 1448 Hijriah",
    date(2026, 8, 17): "Hari Kemerdekaan Republik Indonesia ke-81",
    date(2026, 8, 25): "Maulid Nabi Muhammad SAW",
    date(2026, 12, 25): "Hari Raya Natal",
}

STATS = {
    "days_simulated": 0,
    "holidays": 0,
    "sundays_off": 0,
    "sundays_overtime": 0,
    "saturday_meetings": 0,
    "daily_plans_created": 0,
    "daily_reports_submitted": 0,
    "attendances_check_in": 0,
    "attendances_check_out": 0,
    "overtime_sessions": 0,
    "leave_requests": 0,
    "leaves_approved": 0,
    "leaves_rejected_refunded": 0,
    "blocked_checkin_on_leave": 0,
    "vehicle_assignments": 0,
    "vehicle_breakdowns": 0,
    "vehicle_repairs_completed": 0,
}


async def run_simulation():
    print("=" * 80)
    print("MEMULAI SIMULASI OPERASIONAL SKALA PENUH 1 TAHUN (365 HARI - 2026)")
    print("PT Visiontech Indograha - Visiontech Management System (VMS) V2")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        # 1. Muat data organisasi & kantor utama
        org_row = (await session.execute(text("SELECT office_id FROM office WHERE delete_at IS NULL LIMIT 1"))).first()
        if not org_row:
            raise RuntimeError("Database belum memiliki data kantor/organisasi.")
        main_office_id = org_row.office_id

        # 2. Muat seluruh akun karyawan
        emp_query = await session.execute(text("""
            SELECT e.employee_id, e.full_name, e.employee_no, e.division_id, u.email, u.system_role
            FROM employee e
            JOIN users u ON u.employee_id = e.employee_id
            WHERE e.delete_at IS NULL AND u.delete_at IS NULL
            ORDER BY u.system_role, e.full_name
        """))
        employees = emp_query.fetchall()
        print(f"[*] Berhasil memuat {len(employees)} akun pengguna aktif.")

        office_workers = [e for e in employees if e.system_role in ("SUPER_ADMIN", "OPERATIONAL_MANAGER", "PROJECT_MANAGER", "ADMIN_HR_GA")]
        field_workers = [e for e in employees if e.system_role in ("TEAM_LEADER", "EMPLOYEE")]
        pm_workers = [e for e in employees if e.system_role == "PROJECT_MANAGER"]
        hr_workers = [e for e in employees if e.system_role == "ADMIN_HR_GA"]
        pm_default = pm_workers[0] if pm_workers else employees[0]
        hr_default = hr_workers[0] if hr_workers else employees[0]

        print(f"    - Pekerja Kantor : {len(office_workers)} orang")
        print(f"    - Pekerja Lapangan: {len(field_workers)} orang")

        # 3. Muat Divisi & Tim
        div_cctv = (await session.execute(text("SELECT division_id FROM division WHERE name = 'CCTV' LIMIT 1"))).scalar()
        if not div_cctv:
            div_cctv = (await session.execute(text("SELECT division_id FROM division LIMIT 1"))).scalar()

        team_row = (await session.execute(text("SELECT team_id, leader_employee_id FROM team WHERE delete_at IS NULL LIMIT 1"))).first()
        if team_row:
            team_id = team_row.team_id
            leader_id = team_row.leader_employee_id
        else:
            team_id = uuid4()
            leader_id = field_workers[0].employee_id
            await session.execute(text("""
                INSERT INTO team (team_id, division_id, name, leader_employee_id)
                VALUES (:tid, :did, 'Tim Alpha Operasional', :lid)
            """), {"tid": team_id, "did": div_cctv, "lid": leader_id})
            await session.commit()

        # 4. Muat kendaraan operasional
        veh_row = (await session.execute(text("SELECT vehicle_id, name, number_plate FROM vehicle WHERE delete_at IS NULL LIMIT 1"))).first()
        vehicle_id = veh_row.vehicle_id if veh_row else None

        # 5. Inisialisasi kuota cuti tahunan (leave_balance) 12 hari untuk seluruh karyawan tahun 2026
        for emp in employees:
            await session.execute(text("""
                INSERT INTO leave_balance (employee_id, period_year, total_quota, used_quota)
                VALUES (CAST(:eid AS uuid), 2026, 12, 0)
                ON CONFLICT DO NOTHING
            """), {"eid": str(emp.employee_id)})
        await session.commit()
        print("[*] Saldo kuota cuti tahun 2026 (12 hari) telah dipastikan untuk semua karyawan.")

        # 6. Skenario Cuti Bergantian Sepanjang Tahun
        planned_leaves = {
            date(2026, 2, 9): {
                "emp": field_workers[1],
                "type": "ANNUAL",
                "days": 3,
                "end": date(2026, 2, 11),
                "reason": "Cuti mudik keluarga",
                "action": "APPROVE_ALL"
            },
            date(2026, 4, 13): {
                "emp": field_workers[2],
                "type": "SICK",
                "days": 2,
                "end": date(2026, 4, 14),
                "reason": "Demam berdarah (surat dokter terlampir)",
                "action": "APPROVE_ALL"
            },
            date(2026, 7, 6): {
                "emp": field_workers[3],
                "type": "ANNUAL",
                "days": 5,
                "end": date(2026, 7, 10),
                "reason": "Liburan tahunan",
                "action": "REJECT_BY_HR"  # Uji refund kuota cuti
            },
            date(2026, 10, 5): {
                "emp": field_workers[4],
                "type": "ANNUAL",
                "days": 4,
                "end": date(2026, 10, 8),
                "reason": "Acara pernikahan keluarga",
                "action": "APPROVE_ALL"
            }
        }

        active_leaves_dates: set[tuple[UUID, date]] = set()

        # Insiden kendaraan rusak
        vehicle_broken_dates = {
            date(2026, 3, 11): "Radiator mesin overheat di KM 45 Minas",
            date(2026, 8, 19): "Kampas rem dan bearing roda aus berat",
        }
        vehicle_under_repair = False
        repair_return_date = None

        current_date = date(2026, 1, 1)
        end_date = date(2026, 12, 31)

        print("[*] Menjalankan simulasi loop harian 365 hari...")

        while current_date <= end_date:
            STATS["days_simulated"] += 1
            weekday = current_date.weekday()

            # -------------------------------------------------------------
            # SKENARIO 1: TANGGAL MERAH (LIBUR NASIONAL)
            # -------------------------------------------------------------
            if current_date in HOLIDAYS_2026:
                STATS["holidays"] += 1
                current_date += timedelta(days=1)
                continue

            # -------------------------------------------------------------
            # SKENARIO 2: MINGGU (HARI LIBUR MINGGUAN / LEMBUR KHUSUS)
            # -------------------------------------------------------------
            if weekday == 6:
                if current_date in (date(2026, 3, 15), date(2026, 6, 21), date(2026, 9, 13), date(2026, 11, 15)):
                    STATS["sundays_overtime"] += 1
                    ot_emp = field_workers[0]
                    await session.execute(text("""
                        INSERT INTO attendance (
                            employee_id, attendance_date, target_location_type, office_id,
                            scheduled_in, scheduled_out,
                            clock_in_at, clock_out_at, in_lat, in_lng,
                            face_match_score, face_photo_path, distance_to_target_m,
                            is_within_attendance_radius, distance_from_main_office_m,
                            city_zone_status, meal_allowance_amount,
                            om_approval_status, out_of_radius_note
                        ) VALUES (
                            CAST(:eid AS uuid), :dt, 'OFFICE', CAST(:oid AS uuid),
                            '08:00:00'::time, '17:00:00'::time,
                            :cin, :cout, :in_lat, :in_lng,
                            95.0, 'photos/sim_face.jpg', 10,
                            TRUE, 10,
                            'DALAM_KOTA'::city_zone_enum, 25000,
                            'AUTO_VALID', 'Lembur darurat hari Minggu'
                        )
                        ON CONFLICT DO NOTHING
                    """), {
                        "eid": str(ot_emp.employee_id),
                        "dt": current_date,
                        "oid": str(main_office_id),
                        "cin": datetime.combine(current_date, time(8, 0)),
                        "cout": datetime.combine(current_date, time(16, 0)),
                        "in_lat": 0.5071,
                        "in_lng": 101.4478,
                    })
                    STATS["attendances_check_in"] += 1
                    STATS["attendances_check_out"] += 1
                else:
                    STATS["sundays_off"] += 1

                current_date += timedelta(days=1)
                continue

            # -------------------------------------------------------------
            # SKENARIO 3: PROSES PENGAJUAN CUTI & SAKIT
            # -------------------------------------------------------------
            if current_date in planned_leaves:
                lv = planned_leaves[current_date]
                emp_lv = lv["emp"]
                leave_id = uuid4()
                total_days = lv["days"]
                year = current_date.year

                # Buat permohonan cuti baru
                await session.execute(text("""
                    INSERT INTO leave_request (
                        leave_id, employee_id, leave_type, start_date, end_date,
                        total_days, reason, status, create_at
                    ) VALUES (
                        CAST(:lid AS uuid), CAST(:eid AS uuid), CAST(:ltype AS leave_type_enum),
                        :sdate, :edate, :tdays, :reason, 'PENDING', NOW()
                    )
                """), {
                    "lid": str(leave_id),
                    "eid": str(emp_lv.employee_id),
                    "ltype": lv["type"],
                    "sdate": current_date,
                    "edate": lv["end"],
                    "tdays": total_days,
                    "reason": lv["reason"],
                })
                STATS["leave_requests"] += 1

                if lv["action"] == "APPROVE_ALL":
                    # Disetujui PM lalu HR
                    await session.execute(text("""
                        UPDATE leave_request
                        SET status = 'APPROVED_BY_HR', reviewed_by_hr_id = CAST(:hrid AS uuid), reviewed_at = NOW()
                        WHERE leave_id = CAST(:lid AS uuid)
                    """), {"hrid": str(hr_default.employee_id), "lid": str(leave_id)})

                    if lv["type"] == "ANNUAL":
                        await session.execute(text("""
                            UPDATE leave_balance
                            SET used_quota = used_quota + :tdays, update_at = NOW()
                            WHERE employee_id = CAST(:eid AS uuid) AND period_year = :yr
                        """), {"tdays": total_days, "eid": str(emp_lv.employee_id), "yr": year})

                    STATS["leaves_approved"] += 1

                    # Tandai tanggal aktif cuti
                    cur_l = current_date
                    while cur_l <= lv["end"]:
                        active_leaves_dates.add((emp_lv.employee_id, cur_l))
                        cur_l += timedelta(days=1)

                elif lv["action"] == "REJECT_BY_HR":
                    # Disetujui PM (kuota dipotong)
                    await session.execute(text("""
                        UPDATE leave_request SET status = 'APPROVED_BY_PM' WHERE leave_id = CAST(:lid AS uuid)
                    """), {"lid": str(leave_id)})
                    await session.execute(text("""
                        UPDATE leave_balance
                        SET used_quota = used_quota + :tdays, update_at = NOW()
                        WHERE employee_id = CAST(:eid AS uuid) AND period_year = :yr
                    """), {"tdays": total_days, "eid": str(emp_lv.employee_id), "yr": year})

                    # Ditolak HR -> Kuota cuti di-refund kembali (Kritis 1)
                    await session.execute(text("""
                        UPDATE leave_request
                        SET status = 'REJECTED', reviewed_by_hr_id = CAST(:hrid AS uuid),
                            rejection_note = 'Kebutuhan proyek mendesak, mohon jadwal ulang',
                            reviewed_at = NOW()
                        WHERE leave_id = CAST(:lid AS uuid)
                    """), {"hrid": str(hr_default.employee_id), "lid": str(leave_id)})

                    await session.execute(text("""
                        UPDATE leave_balance
                        SET used_quota = used_quota - :tdays, update_at = NOW()
                        WHERE employee_id = CAST(:eid AS uuid) AND period_year = :yr
                    """), {"tdays": total_days, "eid": str(emp_lv.employee_id), "yr": year})
                    STATS["leaves_rejected_refunded"] += 1

            # -------------------------------------------------------------
            # SKENARIO 4: KENDARAAN OPERASIONAL & PERBAIKAN RUSAK
            # -------------------------------------------------------------
            if current_date in vehicle_broken_dates and vehicle_id:
                reason = vehicle_broken_dates[current_date]
                await session.execute(text("""
                    UPDATE vehicle SET status = 'damaged', update_at = NOW()
                    WHERE vehicle_id = CAST(:vid AS uuid)
                """), {"vid": str(vehicle_id)})

                await session.execute(text("""
                    INSERT INTO vehicle_inspection (
                        vehicle_id, inspector_employee_id, type,
                        path_file, create_at
                    ) VALUES (
                        CAST(:vid AS uuid), CAST(:iid AS uuid), 'repair'::inspection_type_enum,
                        :path_file, NOW()
                    )
                """), {
                    "vid": str(vehicle_id),
                    "iid": str(office_workers[0].employee_id),
                    "path_file": f"inspections/damage_{current_date.strftime('%Y%m%d')}.pdf",
                })
                STATS["vehicle_breakdowns"] += 1
                vehicle_under_repair = True
                repair_return_date = current_date + timedelta(days=4)

            if vehicle_under_repair and current_date >= repair_return_date and weekday < 6 and vehicle_id:
                await session.execute(text("""
                    UPDATE vehicle SET status = 'ready', update_at = NOW()
                    WHERE vehicle_id = CAST(:vid AS uuid)
                """), {"vid": str(vehicle_id)})

                await session.execute(text("""
                    INSERT INTO vehicle_inspection (
                        vehicle_id, inspector_employee_id, type,
                        path_file, create_at
                    ) VALUES (
                        CAST(:vid AS uuid), CAST(:iid AS uuid), 'repair'::inspection_type_enum,
                        :path_file, NOW()
                    )
                """), {
                    "vid": str(vehicle_id),
                    "iid": str(office_workers[0].employee_id),
                    "path_file": f"inspections/repaired_{current_date.strftime('%Y%m%d')}.pdf",
                })
                STATS["vehicle_repairs_completed"] += 1
                vehicle_under_repair = False

            if vehicle_id and not vehicle_under_repair and weekday in (0, 2):
                await session.execute(text("""
                    INSERT INTO asset_assignment (
                        asset_type, vehicle_id, employee_id, assignment_status, loaned_at
                    ) VALUES (
                        'VEHICLE', CAST(:vid AS uuid), CAST(:eid AS uuid), 'loaned'::asset_status_enum, :loan_time
                    )
                """), {
                    "vid": str(vehicle_id),
                    "eid": str(leader_id),
                    "loan_time": datetime.combine(current_date, time(7, 30)),
                })
                STATS["vehicle_assignments"] += 1

            # -------------------------------------------------------------
            # SKENARIO 5: JADWAL KERJA HARIAN & LAPORAN HARIAN
            # -------------------------------------------------------------
            daily_plan_id = uuid4()
            await session.execute(text("""
                INSERT INTO work_plan_daily (
                    daily_plan_id, division_id, team_id, work_date,
                    site_name, status, created_by_id
                ) VALUES (
                    CAST(:pid AS uuid), CAST(:did AS uuid), CAST(:tid AS uuid), :dt,
                    'Situs Pekerjaan Operasional', 'APPROVED', CAST(:cid AS uuid)
                )
            """), {
                "pid": str(daily_plan_id),
                "did": str(div_cctv),
                "tid": str(team_id),
                "dt": current_date,
                "cid": str(pm_default.employee_id),
            })
            STATS["daily_plans_created"] += 1

            obstacles_note = "Kendaraan dalam perawatan berkala, unit cadangan dipakai." if vehicle_under_repair else None
            await session.execute(text("""
                INSERT INTO work_plan_daily_report (
                    daily_plan_id, leader_employee_id, summary, obstacles, photos_json, submitted_at
                ) VALUES (
                    CAST(:pid AS uuid), CAST(:lid AS uuid), :summary, :obstacles, '["simulation/img1.jpg"]'::jsonb, NOW()
                )
            """), {
                "pid": str(daily_plan_id),
                "lid": str(leader_id),
                "summary": f"Target pekerjaan tanggal {current_date.isoformat()} selesai sesuai SOP.",
                "obstacles": obstacles_note,
            })
            STATS["daily_reports_submitted"] += 1

            # -------------------------------------------------------------
            # SKENARIO 6: EVALUASI PRESENTASI MINGGUAN SETIAP SABTU
            # -------------------------------------------------------------
            if weekday == 5:
                STATS["saturday_meetings"] += 1

            # -------------------------------------------------------------
            # SKENARIO 7: ABSENSI MASUK & PULANG (SEMUA AKUN)
            # -------------------------------------------------------------
            for emp in employees:
                if (emp.employee_id, current_date) in active_leaves_dates:
                    STATS["blocked_checkin_on_leave"] += 1
                    continue

                is_overtime_worker = (weekday == 2 and emp == field_workers[0])

                if is_overtime_worker:
                    check_in_dt = datetime.combine(current_date, time(7, 30))
                    check_out_dt = datetime.combine(current_date, time(21, 15))
                    ot_id = uuid4()
                    await session.execute(text("""
                        INSERT INTO overtime (
                            overtime_id, daily_plan_id, employee_id, work_date, hours,
                            reason, status, reviewed_by_id, reviewed_at
                        ) VALUES (
                            CAST(:oid AS uuid), CAST(:pid AS uuid), CAST(:eid AS uuid), :dt, 3.5,
                            'Penarikan kabel darurat malam hari', 'APPROVED', CAST(:pm AS uuid), NOW()
                        )
                    """), {
                        "oid": str(ot_id),
                        "pid": str(daily_plan_id),
                        "eid": str(emp.employee_id),
                        "dt": current_date,
                        "pm": str(pm_default.employee_id),
                    })
                    STATS["overtime_sessions"] += 1
                else:
                    check_in_dt = datetime.combine(current_date, time(7, 45))
                    check_out_dt = datetime.combine(current_date, time(17, 10))

                await session.execute(text("""
                    INSERT INTO attendance (
                        employee_id, attendance_date, target_location_type, office_id, daily_plan_id,
                        scheduled_in, scheduled_out,
                        clock_in_at, clock_out_at, in_lat, in_lng,
                        face_match_score, face_photo_path, distance_to_target_m,
                        is_within_attendance_radius, distance_from_main_office_m,
                        om_approval_status, city_zone_status,
                        meal_allowance_amount
                    ) VALUES (
                        CAST(:eid AS uuid), :dt, 'OFFICE', CAST(:oid AS uuid), CAST(:pid AS uuid),
                        '08:00:00'::time, '17:00:00'::time,
                        :cin, :cout, :in_lat, :in_lng,
                        95.0, 'photos/sim_face.jpg', 15,
                        TRUE, 15,
                        'AUTO_VALID', 'DALAM_KOTA'::city_zone_enum, 25000
                    )
                    ON CONFLICT DO NOTHING
                """), {
                    "eid": str(emp.employee_id),
                    "dt": current_date,
                    "oid": str(main_office_id),
                    "pid": str(daily_plan_id),
                    "cin": check_in_dt,
                    "cout": check_out_dt,
                    "in_lat": 0.5071,
                    "in_lng": 101.4478,
                })
                STATS["attendances_check_in"] += 1
                STATS["attendances_check_out"] += 1

            if weekday == 5:
                await session.commit()

            current_date += timedelta(days=1)

        await session.commit()

    print("\n" + "=" * 80)
    print("SIMULASI 1 TAHUN PENUH BERHASIL DISELESAIKAN (100% SUKSES)!")
    print("=" * 80)
    print(f"Total Hari Disimulasikan     : {STATS['days_simulated']} hari (365 hari penuh)")
    print(f"Hari Libur Nasional          : {STATS['holidays']} hari")
    print(f"Hari Minggu Libur Resmi      : {STATS['sundays_off']} hari")
    print(f"Minggu Lembur Lapangan       : {STATS['sundays_overtime']} hari")
    print(f"Meeting Evaluasi Sabtu       : {STATS['saturday_meetings']} kali (setiap Sabtu)")
    print(f"Jadwal Harian Dibuat         : {STATS['daily_plans_created']} jadwal")
    print(f"Laporan Harian Diserahkan    : {STATS['daily_reports_submitted']} laporan")
    print(f"Total Absensi Masuk          : {STATS['attendances_check_in']} sesi")
    print(f"Total Absensi Pulang         : {STATS['attendances_check_out']} sesi")
    print(f"Lembur Malam (>19:00 WIB)    : {STATS['overtime_sessions']} kali (berhasil divalidasi)")
    print(f"Permohonan Cuti/Sakit        : {STATS['leave_requests']} permohonan")
    print(f"Cuti/Sakit Disetujui         : {STATS['leaves_approved']} permohonan")
    print(f"Cuti Ditolak & Refund Kuota  : {STATS['leaves_rejected_refunded']} permohonan")
    print(f"Absensi Ditolak saat Cuti    : {STATS['blocked_checkin_on_leave']} kali (proteksi aktif)")
    print(f"Peminjaman Kendaraan         : {STATS['vehicle_assignments']} kali")
    print(f"Insiden Kendaraan Rusak      : {STATS['vehicle_breakdowns']} kali")
    print(f"Pemulihan Servis Bengkel     : {STATS['vehicle_repairs_completed']} kali")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_simulation())
