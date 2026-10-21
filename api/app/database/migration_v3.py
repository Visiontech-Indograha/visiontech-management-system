"""
app/database/migration_v3.py

Modul migrasi database dan sinkronisasi media uji otomatis VMS V3.
Menjalankan DDL migrasi untuk:
1. image_requirement (description TEXT)
2. work_completion (Restrukturisasi ke Client Project Order)
3. work_plan_item (Penambahan multi-slot start_time, end_time, completion_id, GPS)
4. document_template_export (Dukungan source_type WEEKLY, DAILY, COMPLETION)
5. attendance_site_visit (Pencatatan check-in multi-lokasi harian)
6. Seeding media uji dari web/dist/foto_test dan web/dist/file_test ke uploads/
"""

from __future__ import annotations

import logging
import shutil
from datetime import date
from pathlib import Path

from sqlalchemy import text

from app.core.time import jakarta_now
from app.database.session import engine

logger = logging.getLogger(__name__)

DDL_STATEMENTS = [
    # 1. image_requirement
    "ALTER TABLE image_requirement ADD COLUMN IF NOT EXISTS description TEXT NULL;",

    # 2. work_completion (Parent Client Order)
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS division_id UUID REFERENCES division(division_id);",
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS pm_id UUID REFERENCES employee(employee_id);",
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS client_name VARCHAR(150) NOT NULL DEFAULT 'Klien Umum';",
    (
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS project_title "
        "VARCHAR(255) NOT NULL DEFAULT 'Pekerjaan Lapangan';"
    ),
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS order_number VARCHAR(50) NULL;",
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS total_target_unit INT NOT NULL DEFAULT 1;",
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS unit_measure VARCHAR(50) NOT NULL DEFAULT 'Unit';",
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS order_status VARCHAR(30) NOT NULL DEFAULT 'ONGOING';",
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS priority_level VARCHAR(20) NOT NULL DEFAULT 'NORMAL';",
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS site_address TEXT NULL;",
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS site_lat NUMERIC(10,7) NULL;",
    "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS site_lng NUMERIC(10,7) NULL;",

    # Nullable columns for draft/ongoing work_completion
    "ALTER TABLE work_completion ALTER COLUMN daily_plan_id DROP NOT NULL;",
    "ALTER TABLE work_completion ALTER COLUMN leader_signer_id DROP NOT NULL;",
    "ALTER TABLE work_completion ALTER COLUMN leader_signature_path DROP NOT NULL;",
    "ALTER TABLE work_completion ALTER COLUMN leader_signed_at DROP NOT NULL;",
    "ALTER TABLE work_completion ALTER COLUMN signature_hash DROP NOT NULL;",

    # 3. work_plan_item multi-slot assignment
    (
        "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS completion_id "
        "UUID NULL REFERENCES work_completion(completion_id);"
    ),
    "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS start_time TIME NULL DEFAULT '08:00:00';",
    "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS end_time TIME NULL DEFAULT '17:00:00';",
    "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS location_name VARCHAR(150) NULL;",
    "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS site_lat NUMERIC(10,7) NULL;",
    "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS site_lng NUMERIC(10,7) NULL;",
    "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS assigned_employee_ids JSONB NULL;",

    # 4. document_template_export
    (
        "ALTER TABLE document_template_export ADD COLUMN IF NOT EXISTS source_type "
        "VARCHAR(30) NOT NULL DEFAULT 'WORK_COMPLETION';"
    ),
    (
        "ALTER TABLE document_template_export ADD COLUMN IF NOT EXISTS daily_plan_id "
        "UUID NULL REFERENCES work_plan_daily(daily_plan_id);"
    ),
    "ALTER TABLE document_template_export ALTER COLUMN completion_id DROP NOT NULL;",

    # 5. Media photo_path columns on asset & personnel tables
    "ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS photo_path VARCHAR(255) NULL;",
    "ALTER TABLE tool ADD COLUMN IF NOT EXISTS photo_path VARCHAR(255) NULL;",
    "ALTER TABLE employee ADD COLUMN IF NOT EXISTS photo_path VARCHAR(255) NULL;",

    # 6. attendance_site_visit
    """
    CREATE TABLE IF NOT EXISTS attendance_site_visit (
        visit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        attendance_id UUID NOT NULL REFERENCES attendance(attendance_id) ON DELETE CASCADE,
        item_id UUID NOT NULL REFERENCES work_plan_item(item_id),
        check_in_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        visit_lat NUMERIC(10,7) NOT NULL,
        visit_lng NUMERIC(10,7) NOT NULL,
        photo_path VARCHAR(255) NOT NULL,
        distance_to_target_m INT NOT NULL,
        is_within_radius BOOLEAN NOT NULL DEFAULT TRUE,
        notes TEXT NULL,
        create_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_site_visit_attendance ON attendance_site_visit(attendance_id);",
    "CREATE INDEX IF NOT EXISTS idx_site_visit_item ON attendance_site_visit(item_id);",

    # file_object & work_plan_attachment kini bagian DDL 06 (db/migration_m5_daily_refs.sql).

    # 6. Jenis titik survei dinamis (docs/37 §9): peran work type, pemasangan lanjutan, status titik.
    "ALTER TABLE work_type ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'WORK' "
    "CHECK (kind IN ('WORK', 'SURVEY_TASK', 'SURVEY_POINT'));",
    "ALTER TABLE work_type ADD COLUMN IF NOT EXISTS follow_up_work_type_id UUID NULL "
    "REFERENCES work_type(work_type_id) ON DELETE SET NULL;",
    "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS point_status VARCHAR(10) NULL "
    "CHECK (point_status IN ('EXISTING', 'PROPOSED'));",
    "CREATE INDEX IF NOT EXISTS idx_work_type_division_kind ON work_type(division_id, kind) WHERE delete_at IS NULL;",
    # 7. Kontak PM ↔ ketua/anggota tim (telepon & WhatsApp dari web/HP).
    "ALTER TABLE employee ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20) NULL;",
]


def sync_media_seed_files() -> list[str]:
    """Menyalin berkas dari vms-photos/uploads atau web/dist ke direktori uploads/."""
    copied_files: list[str] = []

    # Path root proyek
    api_dir = Path(__file__).resolve().parent.parent.parent
    project_root = api_dir.parent

    # Sumber data uji (termasuk path foto dan uploads yang diberikan pengguna)
    foto_candidates = [
        Path("C:/Users/ageng/visiontect-vms/vms-photos"),
        project_root / "web" / "dist" / "foto_test",
        project_root.parent / "vms-photos",
    ]
    file_candidates = [
        Path("C:/Users/ageng/visiontect-vms/uploads"),
        project_root / "web" / "dist" / "file_test",
        project_root.parent / "uploads",
    ]

    foto_src = next((p for p in foto_candidates if p.exists() and any(p.iterdir())), None)
    file_src = next((p for p in file_candidates if p.exists() and any(p.iterdir())), None)

    # Tujuan uploads fisik
    uploads_dir = api_dir / "uploads"
    subdirs = ["employees", "vehicles", "inspections", "tools", "sop", "docs"]
    for s in subdirs:
        (uploads_dir / s).mkdir(parents=True, exist_ok=True)

    photos = list(foto_src.glob("*.*")) if foto_src else []
    docs = list(file_src.rglob("*.*")) if file_src else []

    all_sample_files = photos + docs
    if not all_sample_files:
        logger.warning(
            "Tidak ditemukan file uji di kandidat foto (%s) atau file (%s)",
            foto_candidates,
            file_candidates,
        )
        return copied_files

    # Salin foto ke masing-masing kategori
    for p in photos:
        if not p.is_file():
            continue
        target_name = p.name.replace(" ", "_")
        for s in ["employees", "vehicles", "inspections", "tools", "sop"]:
            dest = uploads_dir / s / target_name
            if not dest.exists():
                shutil.copy2(p, dest)
                copied_files.append(f"/uploads/{s}/{target_name}")

    # Salin dokumen ke docs/
    for d in docs:
        if not d.is_file():
            continue
        doc_name = d.name.replace(" ", "_")
        dest_doc = uploads_dir / "docs" / doc_name
        if not dest_doc.exists():
            shutil.copy2(d, dest_doc)
            copied_files.append(f"/uploads/docs/{doc_name}")

    logger.info("Sinkronisasi media uji selesai: %d berkas tersalin ke %s", len(copied_files), uploads_dir)
    return copied_files


def _activity_log_partition_ddl(today: date, months_ahead: int = 2) -> list[str]:
    """DDL partisi bulanan `app_activity_logs` (bulan ini + `months_ahead` bulan) dan partisi DEFAULT.

    Batas memakai WIB (+07) seperti partisi bawaan Master Schema V2. Tanpa partisi untuk bulan berjalan,
    setiap INSERT jejak audit (login, sinkron offline, dll.) gagal; DEFAULT menampung bila startup terlewat.
    """
    statements = []
    year, month = today.year, today.month
    for _ in range(months_ahead + 1):
        nxt_year, nxt_month = (year + 1, 1) if month == 12 else (year, month + 1)
        statements.append(
            f"CREATE TABLE IF NOT EXISTS app_activity_logs_{year:04d}_{month:02d} PARTITION OF app_activity_logs "
            f"FOR VALUES FROM ('{year:04d}-{month:02d}-01 00:00:00+07') "
            f"TO ('{nxt_year:04d}-{nxt_month:02d}-01 00:00:00+07');"
        )
        year, month = nxt_year, nxt_month
    statements.append("CREATE TABLE IF NOT EXISTS app_activity_logs_default PARTITION OF app_activity_logs DEFAULT;")
    return statements


async def ensure_activity_log_partitions(months_ahead: int = 2) -> None:
    """Pastikan partisi jejak audit tersedia (idempoten; dijalankan setiap startup)."""
    for stmt in _activity_log_partition_ddl(jakarta_now().date(), months_ahead):
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception as e:  # noqa: BLE001
            logger.warning("Partisi app_activity_logs tidak dibuat: %s - %s", stmt[:70], e)


async def apply_v3_migrations() -> None:
    """Menjalankan migrasi DDL dan sinkronisasi media uji ke PostgreSQL."""
    logger.info("Memulai eksekusi DDL Migration VMS V3...")
    await ensure_activity_log_partitions()

    # 1. Jalankan DDL
    for stmt in DDL_STATEMENTS:
        clean_stmt = stmt.strip()
        if not clean_stmt:
            continue
        try:
            async with engine.begin() as conn:
                await conn.execute(text(clean_stmt))
        except Exception as e:  # noqa: BLE001
            logger.warning("DDL statement warning (mungkin sudah terpasang): %s - %s", clean_stmt[:40], e)

    logger.info("DDL Migration VMS V3 berhasil diterapkan ke database!")

    # 2. Sinkronisasi berkas media fisik
    sync_media_seed_files()

    # 3. Seed relasi foto pada database jika masih kosong
    async with engine.begin() as conn:
        # Update contoh SOP image_requirement
        await conn.execute(text("""
            UPDATE image_requirement
            SET path_image = '/uploads/sop/1312298.png',
                description = COALESCE(
                    description,
                    'Ambil foto tegak lurus dengan pencahayaan memadai sesuai standar K3 Visiontech.'
                )
            WHERE path_image IS NULL OR path_image = '' OR path_image LIKE 'http%';
        """))

        # Update foto kendaraan
        await conn.execute(text("""
            UPDATE vehicle
            SET photo_path = '/uploads/vehicles/download_028.jpg'
            WHERE photo_path IS NULL OR photo_path = '' OR photo_path NOT LIKE '/uploads/%';
        """))

        # Update foto peralatan kerja
        await conn.execute(text("""
            UPDATE tool
            SET photo_path = '/uploads/tools/download_029.jpg'
            WHERE photo_path IS NULL OR photo_path = '' OR photo_path NOT LIKE '/uploads/%';
        """))

        # Update foto profil karyawan (keduanya disinkronkan)
        await conn.execute(text("""
            UPDATE employee
            SET photo_path = '/uploads/employees/download_038.jpg',
                profile_photo_path = '/uploads/employees/download_038.jpg'
            WHERE photo_path IS NULL OR photo_path = '' OR photo_path NOT LIKE '/uploads/%';
        """))

        # Buat sampel Work Completion jika tabel masih kosong
        check_wc = await conn.execute(text("SELECT count(*) FROM work_completion;"))
        count_wc = check_wc.scalar() or 0
        if count_wc == 0:
            # Ambil division_id dan employee_id yang valid
            row_div = await conn.execute(text("SELECT division_id FROM division LIMIT 1;"))
            div_id = row_div.scalar()
            row_pm = await conn.execute(text("""
                SELECT e.employee_id FROM employee e
                JOIN users u ON u.employee_id = e.employee_id
                WHERE u.system_role = 'PROJECT_MANAGER' LIMIT 1;
            """))
            pm_id = row_pm.scalar()

            if div_id and pm_id:
                await conn.execute(text("""
                    INSERT INTO work_completion (
                        completion_id, division_id, pm_id, client_name, project_title,
                        order_number, total_target_unit, unit_measure, order_status,
                        priority_level, site_address, site_lat, site_lng,
                        summary_notes, realization_photos_json
                    ) VALUES (
                        gen_random_uuid(), :div_id, :pm_id, 'PT Pertamina EP Asset 1',
                        'Pemasangan 13 Unit CCTV Area Kilang Pangkalan Susu',
                        'WO-2026-PTM-001', 13, 'Unit CCTV', 'ONGOING', 'HIGH',
                        'Pangkalan Susu, Kab. Langkat, Sumatera Utara', 4.0201200, 98.2435100,
                        'Order pemasangan CCTV IP 4K outdoor tahan cuaca & sertifikasi explosion-proof.',
                        '["/uploads/inspections/download_040.jpg", "/uploads/inspections/download_041.jpg"]'::jsonb
                    );

                    INSERT INTO work_completion (
                        completion_id, division_id, pm_id, client_name, project_title,
                        order_number, total_target_unit, unit_measure, order_status,
                        priority_level, site_address, site_lat, site_lng,
                        summary_notes, realization_photos_json
                    ) VALUES (
                        gen_random_uuid(), :div_id, :pm_id, 'PT PLN (Persero) UID Sumut',
                        'Replacement Automatic Gate Portal Gardu Induk Glugur',
                        'WO-2026-PLN-014', 1, 'Unit Gate', 'ONGOING', 'URGENT',
                        'Jl. KL Yos Sudarso, Glugur, Medan', 3.6124000, 98.6738000,
                        'Penggantian motor barrier gate dan integrasi sensor RFID access card.',
                        '["/uploads/inspections/download_028.jpg"]'::jsonb
                    );
                """), {"div_id": div_id, "pm_id": pm_id})
                logger.info("Berhasil menambahkan 2 sampel Work Completion (Order Klien Pertamina & PLN)!")

    logger.info("Seluruh tahapan migrasi VMS V3 dan update data seed berhasil dieksekusi!")
