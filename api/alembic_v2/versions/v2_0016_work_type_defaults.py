"""Bawaan jenis pekerjaan sebagai template (satuan & fase) + satuan pada item jadwal.

- `work_type.unit_measure` (default 'Unit'): satuan yang dipakai otomatis saat item dibuat dari template.
- `work_type.default_phase` (NULL = ikut `kind`): fase item yang dipakai otomatis saat item dibuat dari template.
- `work_plan_item.unit_measure` (NULL): satuan item; diisi dari jenis pekerjaan bila tidak dikirim.

Idempoten: db/06 memuat kolom ini untuk pemasangan baru.

Revision ID: v2_0016
Revises: v2_0015
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0016"
down_revision: str | None = "v2_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE work_type ADD COLUMN IF NOT EXISTS unit_measure VARCHAR(50) NOT NULL DEFAULT 'Unit'")
    op.execute("ALTER TABLE work_type ADD COLUMN IF NOT EXISTS default_phase VARCHAR(30) NULL")
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE work_type ADD CONSTRAINT ck_work_type_default_phase
                CHECK (default_phase IN ('SURVEY','PREPARATION','INSTALLATION','REPLACEMENT','MAINTENANCE'));
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS unit_measure VARCHAR(50) NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE work_plan_item DROP COLUMN IF EXISTS unit_measure")
    op.execute("ALTER TABLE work_type DROP CONSTRAINT IF EXISTS ck_work_type_default_phase")
    op.execute("ALTER TABLE work_type DROP COLUMN IF EXISTS default_phase")
    op.execute("ALTER TABLE work_type DROP COLUMN IF EXISTS unit_measure")
