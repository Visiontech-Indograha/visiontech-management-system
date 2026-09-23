"""fix vms.new_id(): UUIDv7 yang benar untuk PostgreSQL 16

Versi plpgsql yang terpasang di DB dev gagal di setiap panggilan
(`integer & bit` tidak punya operator) sehingga seluruh INSERT ke tabel ber-id default
ditolak. Pengganti ini murni SQL: 48 bit milidetik Unix + bit acak dari
gen_random_uuid(), lalu nibble versi diubah 4 → 7 (bit 52 dan 53). Varian RFC 4122
sudah dibawa gen_random_uuid(). Di PostgreSQL 18 fungsi ini boleh diganti uuidv7().

Revision ID: 0002_fix_new_id
Revises: 29ebb4b66722
Create Date: 2026-09-23
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_fix_new_id"
down_revision: Union[str, Sequence[str], None] = "29ebb4b66722"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vms.new_id() RETURNS uuid
        LANGUAGE sql VOLATILE AS $$
          SELECT encode(
            set_bit(
              set_bit(
                overlay(uuid_send(gen_random_uuid())
                        PLACING substring(int8send(floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint) FROM 3)
                        FROM 1 FOR 6),
                52, 1),
              53, 1),
            'hex')::uuid
        $$;
        """
    )


def downgrade() -> None:
    # Kembali ke bentuk di db/01_schema.sql sebelum perbaikan (UUIDv4 acak) —
    # bukan ke versi plpgsql yang rusak.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vms.new_id() RETURNS uuid
        LANGUAGE sql VOLATILE AS $$ SELECT gen_random_uuid() $$;
        """
    )
