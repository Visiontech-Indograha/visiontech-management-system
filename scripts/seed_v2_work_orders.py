"""
scripts/seed_v2_work_orders.py
Seeder data realistis VMS V2 untuk alur Work Order baru:
1. Client Sites (Cabang/Lokasi Klien ber-geofence & GPS)
2. Master Work Types ber-photo_requirements & default_bom (JSONB)
3. 7 Contoh Client Work Orders mencakup seluruh siklus State Machine:
   - WAITING_SURVEY
   - SURVEY_IN_PROGRESS
   - SURVEY_SUBMITTED (berisi survey_points & photos)
   - READY_TO_EXECUTE (survei disetujui, work_order_items & BOM terkunci)
   - IN_PROGRESS (item sedang dikerjakan tim)
   - COMPLETED (semua item selesai)
   - BAST_SIGNED (sudah tanda tangan digital BAST lengkap dengan verify_hash)

Penggunaan:
    cd api
    .venv/Scripts/python.exe ../scripts/seed_v2_work_orders.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from sqlalchemy import text
from app.database.session import engine


PHOTO_REQ_CCTV = [
    {"slot": "Foto Sebelum", "hint": "Kondisi tiang/bracket sebelum dipasang CCTV", "is_mandatory": True, "sort_order": 1},
    {"slot": "Foto Proses", "hint": "Penarikan kabel dan crimping RJ45", "is_mandatory": True, "sort_order": 2},
    {"slot": "Foto Sesudah", "hint": "Kamera CCTV aktif menyala dan sudut pandang benar", "is_mandatory": True, "sort_order": 3},
]

DEFAULT_BOM_CCTV = [
    {"item_name": "Kamera IP Bullet 4MP", "default_qty": 1.0, "unit": "Unit", "sort_order": 1},
    {"item_name": "Bracket Kamera Wall Mount", "default_qty": 1.0, "unit": "Unit", "sort_order": 2},
    {"item_name": "Kabel UTP Cat6 Outdoor", "default_qty": 50.0, "unit": "Meter", "sort_order": 3},
    {"item_name": "Konektor RJ45 Cat6", "default_qty": 2.0, "unit": "Buah", "sort_order": 4},
]

PHOTO_REQ_ACS = [
    {"slot": "Foto Kondisi Pintu", "hint": "Pintu dan kusen sebelum pemasangan lock", "is_mandatory": True, "sort_order": 1},
    {"slot": "Foto Instalasi Lock", "hint": "Pemasangan magnetic lock / drop bolt", "is_mandatory": True, "sort_order": 2},
    {"slot": "Foto Uji Akses", "hint": "Pengujian tap kartu / face terminal sukses", "is_mandatory": True, "sort_order": 3},
]

DEFAULT_BOM_ACS = [
    {"item_name": "Access Control Terminal / Reader", "default_qty": 1.0, "unit": "Unit", "sort_order": 1},
    {"item_name": "Magnetic Lock 600 Lbs + Bracket", "default_qty": 1.0, "unit": "Set", "sort_order": 2},
    {"item_name": "Emergency Exit Button", "default_qty": 1.0, "unit": "Unit", "sort_order": 3},
    {"item_name": "Kabel Belden 8 Core", "default_qty": 30.0, "unit": "Meter", "sort_order": 4},
]


async def seed() -> None:
    print("=== SEEDING VMS V2 WORK ORDER REVAMP ===")
    async with engine.connect() as conn:
        tx = await conn.begin()
        try:
            # 1. Cari atau buat Klien
            client_row = (await conn.execute(text(
                "SELECT client_id FROM client WHERE lower(name) LIKE '%pertamina%' AND delete_at IS NULL LIMIT 1"
            ))).first()
            if not client_row:
                client_id = uuid4()
                await conn.execute(text(
                    "INSERT INTO client (client_id, client_code, name, address, pic_name, pic_phone) "
                    "VALUES (:id, 'CLI-PHR', 'PT Pertamina Hulu Rokan', 'Rumbai Camp, Pekanbaru', 'Ir. Bambang Tri', '08117500123')"
                ), {"id": client_id})
                print("+ Dibuat Klien: PT Pertamina Hulu Rokan")
            else:
                client_id = client_row[0]
                print(f"= Menggunakan Klien yang ada: {client_id}")

            # 2. Cari atau buat Sites (Cabang Klien)
            sites_data = [
                ("Minas Gathering Station #1", "Jl. Minas - Perawang KM 12, Siak", 0.7234500, 101.4521000, 150, "Ahmad Subagio", "081234567890"),
                ("Duri Central Facility Hub", "Duri Field Area 4, Mandau, Bengkalis", 1.2856200, 101.2145300, 200, "Bambang Wijaya", "081298765432"),
                ("Dumai Wharf Terminal 02", "Kawasan Pelabuhan PHR Dumai", 1.6821100, 101.4390200, 120, "Hendra Gunawan", "081377889900"),
            ]
            site_ids = []
            for s_name, s_addr, s_lat, s_lng, s_rad, s_pic, s_phone in sites_data:
                existing_site = (await conn.execute(text(
                    "SELECT site_id FROM client_sites WHERE client_id = :c AND site_name = :n AND delete_at IS NULL"
                ), {"c": client_id, "n": s_name})).scalar()
                if not existing_site:
                    sid = uuid4()
                    await conn.execute(text(
                        "INSERT INTO client_sites (site_id, client_id, site_name, address, latitude, longitude, geofence_radius_meters, pic_name, pic_phone) "
                        "VALUES (:id, :c, :n, :a, :lat, :lng, :r, :pic, :phone)"
                    ), {"id": sid, "c": client_id, "n": s_name, "a": s_addr, "lat": s_lat, "lng": s_lng, "r": s_rad, "pic": s_pic, "phone": s_phone})
                    site_ids.append(sid)
                    print(f"+ Dibuat Site: {s_name}")
                else:
                    site_ids.append(existing_site)
                    print(f"= Menggunakan Site yang ada: {s_name}")

            # 3. Cari Divisi & PM
            div_row = (await conn.execute(text(
                "SELECT division_id FROM division WHERE delete_at IS NULL ORDER BY create_at ASC LIMIT 1"
            ))).first()
            if not div_row:
                sys.exit("Gagal: Tidak ada divisi di database!")
            division_id = div_row[0]

            pm_row = (await conn.execute(text(
                "SELECT employee_id FROM employee WHERE delete_at IS NULL LIMIT 1"
            ))).first()
            if not pm_row:
                sys.exit("Gagal: Tidak ada employee/PM di database!")
            pm_id = pm_row[0]

            team_row = (await conn.execute(text(
                "SELECT team_id FROM team WHERE delete_at IS NULL LIMIT 1"
            ))).first()
            team_id = team_row[0] if team_row else None

            # 4. Update Work Types dengan photo_requirements & default_bom
            wt_rows = (await conn.execute(text(
                "SELECT work_type_id, name FROM work_type WHERE delete_at IS NULL"
            ))).fetchall()
            cctv_wt_id = None
            for wt_id, wt_name in wt_rows:
                if "cctv" in wt_name.lower():
                    cctv_wt_id = wt_id
                    await conn.execute(text(
                        "UPDATE work_type SET photo_requirements = CAST(:pr AS jsonb), default_bom = CAST(:db AS jsonb) "
                        "WHERE work_type_id = :id"
                    ), {"id": wt_id, "pr": json.dumps(PHOTO_REQ_CCTV), "db": json.dumps(DEFAULT_BOM_CCTV)})
                elif "acs" in wt_name.lower() or "access" in wt_name.lower():
                    await conn.execute(text(
                        "UPDATE work_type SET photo_requirements = CAST(:pr AS jsonb), default_bom = CAST(:db AS jsonb) "
                        "WHERE work_type_id = :id"
                    ), {"id": wt_id, "pr": json.dumps(PHOTO_REQ_ACS), "db": json.dumps(DEFAULT_BOM_ACS)})
            
            if not cctv_wt_id and wt_rows:
                cctv_wt_id = wt_rows[0][0]
                await conn.execute(text(
                    "UPDATE work_type SET photo_requirements = CAST(:pr AS jsonb), default_bom = CAST(:db AS jsonb) "
                    "WHERE work_type_id = :id"
                ), {"id": cctv_wt_id, "pr": json.dumps(PHOTO_REQ_CCTV), "db": json.dumps(DEFAULT_BOM_CCTV)})
            print("+ Diperbarui Work Type photo_requirements & default_bom (JSONB)")

            now = datetime.now(timezone.utc)

            # 5. Seed Work Orders
            orders_data = [
                {
                    "wo_number": "WO-202611-001",
                    "title": "Pemasangan Baru 8 Titik CCTV Gate Minas",
                    "complaint": "Area gerbang utama Minas membutuhkan monitoring visual 24 jam untuk pengawasan keluar masuk truk tangki.",
                    "status": "WAITING_SURVEY",
                    "site_idx": 0,
                    "lead_team": None,
                },
                {
                    "wo_number": "WO-202611-002",
                    "title": "Survei Penarikan Jalur FO Duri Hub",
                    "complaint": "Koneksi jaringan antar gedung facility sering terputus, dibutuhkan jalur fiber optik redundan.",
                    "status": "SURVEY_IN_PROGRESS",
                    "site_idx": 1,
                    "lead_team": team_id,
                    "survey_assigned_at": now - timedelta(days=2),
                },
                {
                    "wo_number": "WO-202611-003",
                    "title": "Upgrade Access Control Room Dumai",
                    "complaint": "Kunci magnetic pintu server room sering macet, butuh upgrade ke face recognition dan multi-door controller.",
                    "status": "SURVEY_SUBMITTED",
                    "site_idx": 2,
                    "lead_team": team_id,
                    "survey_assigned_at": now - timedelta(days=3),
                    "survey_submitted_at": now - timedelta(hours=4),
                },
                {
                    "wo_number": "WO-202611-004",
                    "title": "Instalasi Perimeter CCTV Duri Field",
                    "complaint": "Pagar sisi timur rawan penyusupan, diperlukan 4 titik kamera bullet night vision.",
                    "status": "READY_TO_EXECUTE",
                    "site_idx": 1,
                    "lead_team": team_id,
                    "survey_assigned_at": now - timedelta(days=5),
                    "survey_submitted_at": now - timedelta(days=2),
                    "survey_approved_at": now - timedelta(days=1),
                },
                {
                    "wo_number": "WO-202611-005",
                    "title": "Penarikan Kabel FO Minas Station",
                    "complaint": "Kabel FO eksisting putus terkena alat berat di jalur KM 12.",
                    "status": "IN_PROGRESS",
                    "site_idx": 0,
                    "lead_team": team_id,
                    "survey_assigned_at": now - timedelta(days=7),
                    "survey_submitted_at": now - timedelta(days=4),
                    "survey_approved_at": now - timedelta(days=3),
                },
                {
                    "wo_number": "WO-202611-006",
                    "title": "Maintenance Rutin & Pembersihan Lensa Minas",
                    "complaint": "Pemeliharaan berkala 16 kamera CCTV dan server NVR.",
                    "status": "COMPLETED",
                    "site_idx": 0,
                    "lead_team": team_id,
                    "survey_assigned_at": now - timedelta(days=10),
                    "survey_submitted_at": now - timedelta(days=8),
                    "survey_approved_at": now - timedelta(days=7),
                },
                {
                    "wo_number": "WO-202611-007",
                    "title": "Penggantian Kamera CCTV Wharf Dumai",
                    "complaint": "Kamera dermaga korosi akibat uap air laut, butuh penggantian unit stainless steel IP67.",
                    "status": "BAST_SIGNED",
                    "site_idx": 2,
                    "lead_team": team_id,
                    "survey_assigned_at": now - timedelta(days=14),
                    "survey_submitted_at": now - timedelta(days=12),
                    "survey_approved_at": now - timedelta(days=11),
                    "bast_signed_at": now - timedelta(days=1),
                    "bast_signer_name": "Hendra Gunawan (Site Manager)",
                    "verify_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                },
            ]

            for o in orders_data:
                wo_id = (await conn.execute(text(
                    "SELECT work_order_id FROM client_work_orders WHERE wo_number = :wo"
                ), {"wo": o["wo_number"]})).scalar()

                site_id = site_ids[o["site_idx"]]

                if not wo_id:
                    wo_id = uuid4()
                    await conn.execute(text("""
                        INSERT INTO client_work_orders (
                            work_order_id, wo_number, client_id, client_site_id, division_id,
                            pm_id, lead_team_id, title, initial_complaint, status,
                            survey_assigned_at, survey_submitted_at, survey_approved_at,
                            bast_signed_at, bast_signer_name, verify_hash
                        ) VALUES (
                            :wo_id, :wo_num, :c_id, :s_id, :div_id,
                            :pm_id, :team_id, :title, :complaint, :status,
                            :s_assigned, :s_sub, :s_app,
                            :bast_signed, :bast_signer, :v_hash
                        )
                    """), {
                        "wo_id": wo_id,
                        "wo_num": o["wo_number"],
                        "c_id": client_id,
                        "s_id": site_id,
                        "div_id": division_id,
                        "pm_id": pm_id,
                        "team_id": o["lead_team"],
                        "title": o["title"],
                        "complaint": o["complaint"],
                        "status": o["status"],
                        "s_assigned": o.get("survey_assigned_at"),
                        "s_sub": o.get("survey_submitted_at"),
                        "s_app": o.get("survey_approved_at"),
                        "bast_signed": o.get("bast_signed_at"),
                        "bast_signer": o.get("bast_signer_name"),
                        "v_hash": o.get("verify_hash"),
                    })
                    print(f"+ Dibuat WO [{o['status']}]: {o['wo_number']} - {o['title']}")

                # Jika status SURVEY_SUBMITTED atau setelahnya, buat record survei
                if o["status"] in ("SURVEY_SUBMITTED", "READY_TO_EXECUTE", "IN_PROGRESS", "COMPLETED", "BAST_SIGNED"):
                    surv_id = (await conn.execute(text(
                        "SELECT survey_id FROM work_order_surveys WHERE work_order_id = :wo"
                    ), {"wo": wo_id})).scalar()
                    if not surv_id:
                        surv_id = uuid4()
                        await conn.execute(text("""
                            INSERT INTO work_order_surveys (
                                survey_id, work_order_id, surveyor_team_id, survey_date,
                                narrative, format, status, submitted_at, approved_at
                            ) VALUES (
                                :sid, :wo_id, :tid, :sdate,
                                :narrative, 'CCTV', :st, :sub_at, :app_at
                            )
                        """), {
                            "sid": surv_id,
                            "wo_id": wo_id,
                            "tid": team_id,
                            "sdate": date.today() - timedelta(days=2),
                            "narrative": "Survei lapangan telah dilaksanakan bersama perwakilan klien. Titik pemasangan dan jalur kabel sudah disepakati.",
                            "st": "APPROVED" if o.get("survey_approved_at") else "SUBMITTED",
                            "sub_at": o.get("survey_submitted_at"),
                            "app_at": o.get("survey_approved_at"),
                        })

                        # Buat 2 Titik Survei
                        p1_id = uuid4()
                        p2_id = uuid4()
                        await conn.execute(text("""
                            INSERT INTO work_order_survey_points (
                                point_id, work_order_id, survey_id, point_name,
                                location_detail, site_lat, site_lng, recommended_work_type_id,
                                recommended_bom, remarks, status
                            ) VALUES 
                            (:p1, :wo_id, :sid, 'Titik A - Pintu Masuk Gerbang', 'Sisi tiang lampu selatan, tinggi 4.5m', 0.72350, 101.45220, :wt, :bom, 'Arah hadap masuk kendaraan', 'TODO'),
                            (:p2, :wo_id, :sid, 'Titik B - Area Parkir Truk', 'Dinding pos jaga timur, tinggi 3.8m', 0.72360, 101.45230, :wt, :bom, 'Coverage area parkir 180 derajat', 'TODO')
                        """), {
                            "p1": p1_id, "p2": p2_id, "wo_id": wo_id, "sid": surv_id,
                            "wt": cctv_wt_id, "bom": json.dumps(DEFAULT_BOM_CCTV)
                        })

                # Jika status READY_TO_EXECUTE atau setelahnya, pastikan ada work_order_items & BOM
                if o["status"] in ("READY_TO_EXECUTE", "IN_PROGRESS", "COMPLETED", "BAST_SIGNED"):
                    item_count = (await conn.execute(text(
                        "SELECT count(*) FROM work_order_items WHERE work_order_id = :wo"
                    ), {"wo": wo_id})).scalar() or 0

                    if item_count == 0:
                        it1_status = "DONE" if o["status"] in ("COMPLETED", "BAST_SIGNED") else ("IN_PROGRESS" if o["status"] == "IN_PROGRESS" else "PENDING")
                        it2_status = "DONE" if o["status"] in ("COMPLETED", "BAST_SIGNED") else "PENDING"
                        it1_qty = 1 if it1_status == "DONE" else 0
                        it2_qty = 1 if it2_status == "DONE" else 0

                        it1_id = uuid4()
                        it2_id = uuid4()
                        await conn.execute(text("""
                            INSERT INTO work_order_items (
                                item_id, work_order_id, work_type_id, title,
                                location_detail, target_qty, completed_qty, photo_slots_snapshot, status
                            ) VALUES
                            (:i1, :wo, :wt, 'Instalasi Kamera Gerbang Utama', 'Tiang selatan KM 12', 1, :q1, :ph, :s1),
                            (:i2, :wo, :wt, 'Instalasi Kamera Area Parkir Truk', 'Pos jaga timur', 1, :q2, :ph, :s2)
                        """), {
                            "i1": it1_id, "i2": it2_id, "wo": wo_id, "wt": cctv_wt_id,
                            "q1": it1_qty, "q2": it2_qty, "ph": json.dumps(PHOTO_REQ_CCTV),
                            "s1": it1_status, "s2": it2_status
                        })

                        # Tambahkan BOM untuk items
                        await conn.execute(text("""
                            INSERT INTO work_order_bom (
                                bom_id, work_order_id, work_order_item_id, item_name,
                                unit, estimated_qty, actual_qty
                            ) VALUES
                            (gen_random_uuid(), :wo, :i1, 'Kamera IP Bullet 4MP', 'Unit', 1, :a1),
                            (gen_random_uuid(), :wo, :i1, 'Kabel UTP Cat6 Outdoor', 'Meter', 50, :a2),
                            (gen_random_uuid(), :wo, :i2, 'Kamera IP Bullet 4MP', 'Unit', 1, :a1),
                            (gen_random_uuid(), :wo, :i2, 'Kabel UTP Cat6 Outdoor', 'Meter', 40, :a2)
                        """), {
                            "wo": wo_id, "i1": it1_id, "i2": it2_id,
                            "a1": 1 if o["status"] in ("COMPLETED", "BAST_SIGNED") else 0,
                            "a2": 45 if o["status"] in ("COMPLETED", "BAST_SIGNED") else 0,
                        })

            await tx.commit()
            print("=== SEEDING SELESAI DENGAN SUKSES! ===")
        except Exception as e:
            await tx.rollback()
            print(f"Error seeding: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed())
