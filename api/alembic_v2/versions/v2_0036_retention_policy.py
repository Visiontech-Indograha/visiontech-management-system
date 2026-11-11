"""Kebijakan retensi (`retention_policy`), log jalan (`retention_run_log`), `employee.separated_at`, indeks arsip.

Expand murni: tabel baru, kolom NULLABLE, indeks parsial `WHERE delete_at IS NOT NULL` (CONCURRENTLY).
Semua kebijakan awal `is_active = FALSE` (job tidak menghapus apa pun sebelum pemilik mengaktifkan).

Titik awal 30 hari berkas pribadi karyawan = `employee.separated_at` (diisi saat offboarding COMPLETED;
backfill dari `employee_offboarding.effective_date` berstatus COMPLETED). `offboarding_status='offboarded'`
tidak menyimpan waktu dan `update_at` berubah-ubah, jadi ambigu dan tidak dipakai.

Revision ID: v2_0036
Revises: v2_0035
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0036"
down_revision: str | None = "v2_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ARCHIVE_INDEXES = [
    ("employee", "ix_employee_archived_delete_at"),
    ("client", "ix_client_archived_delete_at"),
    ("employee_file", "ix_employee_file_archived_delete_at"),
    ("tool", "ix_tool_archived_delete_at"),
    ("vehicle", "ix_vehicle_archived_delete_at"),
    ("vehicle_file", "ix_vehicle_file_archived_delete_at"),
    ("vehicle_inspection", "ix_vehicle_inspection_archived_delete_at"),
    ("company_mess", "ix_company_mess_archived_delete_at"),
    ("division", "ix_division_archived_delete_at"),
    ("job_position", "ix_job_position_archived_delete_at"),
]

SEED = [
    ("employee_row", 1825), ("client", 1825), ("employee_file", 1825),
    ("tool", 730), ("vehicle", 730),
    ("company_mess", 365), ("division", 365), ("job_position", 365),
    ("employee_personal_files", 30),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS retention_policy (
            data_type      VARCHAR(60) PRIMARY KEY,
            retention_days INTEGER NOT NULL CHECK (retention_days > 0),
            is_active      BOOLEAN NOT NULL DEFAULT FALSE,
            updated_by     UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
            update_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS retention_run_log (
            run_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            mode    VARCHAR(10) NOT NULL CHECK (mode IN ('cek', 'terapkan')),
            counts  JSONB NOT NULL DEFAULT '{}'::jsonb,
            status  VARCHAR(10) NOT NULL CHECK (status IN ('berhasil', 'gagal', 'sebagian')),
            detail  TEXT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_retention_run_log_run_at ON retention_run_log (run_at DESC)")
    for dtype, days in SEED:
        op.execute(
            f"INSERT INTO retention_policy (data_type, retention_days) VALUES ('{dtype}', {days}) "
            "ON CONFLICT (data_type) DO NOTHING"
        )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON retention_policy, retention_run_log TO vms_api;
            END IF;
        END $$
        """
    )
    op.execute("ALTER TABLE employee ADD COLUMN IF NOT EXISTS separated_at TIMESTAMPTZ NULL")
    # Backfill sekali jalan (tabel karyawan kecil); hanya yang sudah selesai offboarding dan belum terisi.
    op.execute(
        """
        UPDATE employee e SET separated_at = x.eff
        FROM (SELECT employee_id, max(effective_date)::timestamptz AS eff
              FROM employee_offboarding WHERE status = 'COMPLETED' AND delete_at IS NULL
              GROUP BY employee_id) x
        WHERE e.employee_id = x.employee_id AND e.separated_at IS NULL
        """
    )
    with op.get_context().autocommit_block():
        for table, name in ARCHIVE_INDEXES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {table} (delete_at) "
                "WHERE delete_at IS NOT NULL"
            )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_employee_separated_at ON employee (separated_at) "
            "WHERE separated_at IS NOT NULL"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_employee_separated_at")
        for _table, name in ARCHIVE_INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
    op.execute("ALTER TABLE employee DROP COLUMN IF EXISTS separated_at")
    op.execute("DROP TABLE IF EXISTS retention_run_log")
    op.execute("DROP TABLE IF EXISTS retention_policy")
