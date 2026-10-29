"""Aset & mess per tim (butir 7): `tool.team_id` dan `vehicle.team_id` = tim pemakai bawaan; `company_mess_stay.team_id`
= tim yang menginap di mess (kapasitas per tanggal dihitung dari hunian tim ini dan lainnya).

Kolom NULL = belum terikat tim. Hapus tim (ON DELETE SET NULL) melepas ikatan. Idempoten: db/06 memuat kolom ini untuk
pemasangan baru.

Revision ID: v2_0015
Revises: v2_0014
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0015"
down_revision: str | None = "v2_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLES = (
    ("tool", "fk_tool_team"),
    ("vehicle", "fk_vehicle_team"),
    ("company_mess_stay", "fk_mess_stay_team"),
)
_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS ix_company_mess_stay_team_dates "
    "ON company_mess_stay (team_id, stay_start_date)"
)


def upgrade() -> None:
    for table, fk in _TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS team_id uuid NULL")
        op.execute(
            f"""
            DO $$ BEGIN
                ALTER TABLE {table} ADD CONSTRAINT {fk}
                    FOREIGN KEY (team_id) REFERENCES team(team_id) ON DELETE SET NULL;
            EXCEPTION WHEN duplicate_object THEN NULL; END $$;
            """
        )
    op.execute(_INDEX_SQL)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_company_mess_stay_team_dates")
    for table, fk in _TABLES:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {fk}")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS team_id")
