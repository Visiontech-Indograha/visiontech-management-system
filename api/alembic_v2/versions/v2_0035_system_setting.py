"""Tabel `system_setting`: flag fitur yang boleh diubah SUPER_ADMIN saat server berjalan.

Expand murni: tabel baru, kosong. Tanpa baris, nilai efektif = env (perilaku produksi tidak berubah).
Prioritas nilai: SYSTEM_SETTINGS_FORCE (env) > tabel ini > env biasa. Lihat app/core/system_settings.py.

Revision ID: v2_0035
Revises: v2_0034
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0035"
down_revision: str | None = "v2_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS system_setting (
            key        VARCHAR(80) PRIMARY KEY,
            value      JSONB NOT NULL,
            updated_by UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
            update_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    # Peran runtime (non-superuser) bila ada; default privileges biasanya sudah menutupi, ini penjamin.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON system_setting TO vms_api;
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS system_setting")
