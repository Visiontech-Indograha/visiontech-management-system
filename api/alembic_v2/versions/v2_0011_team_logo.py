"""Logo tim (Master Schema V2): kolom `team.logo_file_id` menunjuk berkas logo di `file_object`.

Logo tim dipakai di seluruh dokumen tim (laporan harian/mingguan, BAST, surat tugas, survei) dan foto berwatermark.
Kolom NULL = memakai logo default Visiontech. Hapus berkas (ON DELETE SET NULL) mengembalikan tim ke default.
Idempoten: db/06 sudah memuat kolom ini untuk pemasangan baru.

Revision ID: v2_0011
Revises: v2_0010
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0011"
down_revision: str | None = "v2_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE team ADD COLUMN IF NOT EXISTS logo_file_id uuid NULL")
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE team ADD CONSTRAINT fk_team_logo_file
                FOREIGN KEY (logo_file_id) REFERENCES file_object(id) ON DELETE SET NULL;
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE team DROP CONSTRAINT IF EXISTS fk_team_logo_file")
    op.execute("ALTER TABLE team DROP COLUMN IF EXISTS logo_file_id")
