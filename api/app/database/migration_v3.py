"""Runtime maintenance for the Master Schema V2 API."""

from __future__ import annotations

import logging
import shutil
from datetime import date
from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.core.time import jakarta_now
from app.database.session import engine

logger = logging.getLogger(__name__)


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


async def ensure_schema_extensions() -> None:
    """Memastikan ekstensi skema tabel laporan harian & revisi order telah terpasang."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS work_plan_daily_report (
            report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            daily_plan_id UUID NOT NULL REFERENCES work_plan_daily(daily_plan_id) ON DELETE CASCADE,
            leader_employee_id UUID NOT NULL REFERENCES employee(employee_id),
            summary TEXT NOT NULL,
            obstacles TEXT NULL,
            photos_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delete_at TIMESTAMPTZ NULL,
            CONSTRAINT uq_work_plan_daily_report_plan UNIQUE (daily_plan_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS work_completion_revision (
            revision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            completion_id UUID NOT NULL REFERENCES work_completion(completion_id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            request_date DATE NOT NULL DEFAULT CURRENT_DATE,
            survey_task_id UUID NULL REFERENCES work_plan_item(item_id) ON DELETE SET NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
            created_by_id UUID NULL REFERENCES employee(employee_id),
            create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delete_at TIMESTAMPTZ NULL
        );
        """,
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS client_id UUID NULL;",
        (
            "ALTER TABLE work_completion ADD CONSTRAINT fk_work_completion_client "
            "FOREIGN KEY (client_id) REFERENCES client(client_id);"
        ),
        "ALTER TABLE work_completion ALTER COLUMN client_name DROP NOT NULL;",
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_status VARCHAR(30) NULL DEFAULT 'MENUNGGU_ACC';",
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_decided_at TIMESTAMPTZ NULL;",
        (
            "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_decided_by_id "
            "UUID NULL REFERENCES employee(employee_id);"
        ),
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_notes TEXT NULL;",
        "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'PLAN';",
        (
            "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS revision_id "
            "UUID NULL REFERENCES work_completion_revision(revision_id);"
        ),
    ]
    async with engine.begin() as conn:
        for stmt in statements:
            try:
                await conn.execute(text(stmt.strip()))
            except Exception as e:  # noqa: BLE001
                logger.warning("Skema ekstensi dilewati/gagal: %s - %s", stmt.strip()[:60], e)


async def prepare_v2_runtime() -> None:
    """Maintain time-based audit partitions, schema extensions and optional demo data at startup."""
    await ensure_activity_log_partitions()
    await ensure_schema_extensions()
    if not settings.SEED_DEMO_MEDIA:
        return
    await _seed_demo_media()


_DEMO_ORDERS = (
    """
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
                        )
    """,
    """
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
                        )
    """,
)


async def _seed_demo_media() -> None:
    """Media & order contoh untuk lingkungan demo (SEED_DEMO_MEDIA=true)."""
    # 2. Sinkronisasi berkas media fisik
    sync_media_seed_files()

    # 3. Seed relasi foto pada database jika masih kosong
    async with engine.begin() as conn:
        # Update contoh SOP image_requirement
        await conn.execute(
            text("""
            UPDATE image_requirement
            SET path_image = '/uploads/sop/1312298.png',
                description = COALESCE(
                    description,
                    'Ambil foto tegak lurus dengan pencahayaan memadai sesuai standar K3 Visiontech.'
                )
            WHERE path_image IS NULL OR path_image = '' OR path_image LIKE 'http%';
        """)
        )

        # Update foto kendaraan
        await conn.execute(
            text("""
            UPDATE vehicle
            SET photo_path = '/uploads/vehicles/download_028.jpg'
            WHERE photo_path IS NULL OR photo_path = '' OR photo_path NOT LIKE '/uploads/%';
        """)
        )

        # Update foto peralatan kerja
        await conn.execute(
            text("""
            UPDATE tool
            SET photo_path = '/uploads/tools/download_029.jpg'
            WHERE photo_path IS NULL OR photo_path = '' OR photo_path NOT LIKE '/uploads/%';
        """)
        )

        # Update foto profil karyawan (keduanya disinkronkan)
        await conn.execute(
            text("""
            UPDATE employee
            SET photo_path = '/uploads/employees/download_038.jpg',
                profile_photo_path = '/uploads/employees/download_038.jpg'
            WHERE photo_path IS NULL OR photo_path = '' OR photo_path NOT LIKE '/uploads/%';
        """)
        )

        # Buat sampel Work Completion jika tabel masih kosong
        check_wc = await conn.execute(text("SELECT count(*) FROM work_completion;"))
        count_wc = check_wc.scalar() or 0
        if count_wc == 0:
            # Ambil division_id dan employee_id yang valid
            row_div = await conn.execute(text("SELECT division_id FROM division LIMIT 1;"))
            div_id = row_div.scalar()
            row_pm = await conn.execute(
                text("""
                SELECT e.employee_id FROM employee e
                JOIN users u ON u.employee_id = e.employee_id
                WHERE u.system_role = 'PROJECT_MANAGER' LIMIT 1;
            """)
            )
            pm_id = row_pm.scalar()

            if div_id and pm_id:
                # asyncpg menolak beberapa perintah ber-parameter sekaligus -> jalankan satu per satu.
                for insert_sql in _DEMO_ORDERS:
                    await conn.execute(text(insert_sql), {"div_id": div_id, "pm_id": pm_id})
                logger.info("Berhasil menambahkan 2 sampel Work Completion (Order Klien Pertamina & PLN)!")

    logger.info("Seluruh tahapan migrasi VMS V3 dan update data seed berhasil dieksekusi!")
