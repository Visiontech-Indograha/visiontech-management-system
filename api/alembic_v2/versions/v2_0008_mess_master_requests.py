"""Mess: master lokasi mess (dipilih, bukan diketik ulang) + pengajuan hunian oleh karyawan yang diputus PM/OM/HR.

Revision ID: v2_0008
Revises: v2_0007
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0008"
down_revision: str | None = "v2_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_mess (
            mess_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            mess_name VARCHAR(150) NOT NULL,
            city VARCHAR(100) NOT NULL,
            address TEXT NOT NULL,
            latitude NUMERIC(10,7) NULL,
            longitude NUMERIC(10,7) NULL,
            capacity INTEGER NULL CHECK (capacity IS NULL OR capacity > 0),
            create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delete_at TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        """
        ALTER TABLE company_mess_stay
            ADD COLUMN IF NOT EXISTS mess_id UUID NULL REFERENCES company_mess(mess_id),
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'APPROVED',
            ADD COLUMN IF NOT EXISTS requested_by_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS request_note TEXT NULL,
            ADD COLUMN IF NOT EXISTS decided_by_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS decided_at TIMESTAMPTZ NULL,
            ADD COLUMN IF NOT EXISTS decision_note TEXT NULL,
            ALTER COLUMN latitude DROP NOT NULL,
            ALTER COLUMN longitude DROP NOT NULL,
            ALTER COLUMN mess_name TYPE VARCHAR(150)
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE company_mess_stay ADD CONSTRAINT ck_mess_stay_status
                CHECK (status IN ('REQUESTED','APPROVED','REJECTED','CANCELLED'));
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
        """
    )
    # Hunian lama (teks bebas) → satu baris master per kombinasi nama+kota+alamat, lalu ditautkan.
    op.execute(
        """
        INSERT INTO company_mess (mess_name, city, address, latitude, longitude)
        SELECT DISTINCT ON (mess_name, city, address) mess_name, city, address, latitude, longitude
        FROM company_mess_stay WHERE delete_at IS NULL AND mess_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE company_mess_stay s SET mess_id = m.mess_id
        FROM company_mess m
        WHERE s.mess_id IS NULL AND m.mess_name = s.mess_name AND m.city = s.city AND m.address = s.address
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_mess_stay_mess ON company_mess_stay (mess_id) WHERE delete_at IS NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mess_stay_status ON company_mess_stay (status) WHERE delete_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_mess_stay_status")
    op.execute("DROP INDEX IF EXISTS ix_mess_stay_mess")
    op.execute("ALTER TABLE company_mess_stay DROP CONSTRAINT IF EXISTS ck_mess_stay_status")
    op.execute(
        """
        ALTER TABLE company_mess_stay
            DROP COLUMN IF EXISTS decision_note, DROP COLUMN IF EXISTS decided_at,
            DROP COLUMN IF EXISTS decided_by_user_id, DROP COLUMN IF EXISTS request_note,
            DROP COLUMN IF EXISTS requested_by_user_id, DROP COLUMN IF EXISTS status,
            DROP COLUMN IF EXISTS mess_id
        """
    )
    op.execute("DROP TABLE IF EXISTS company_mess")
