"""Status wajah absen eksplisit (Master Schema V2): kolom `attendance.face_status`.

Absen yang tidak diverifikasi wajahnya (tidak diperiksa, belum terdaftar, layanan wajah mati) kini bertanda
eksplisit alih-alih hanya skor 0. Data lama diisi dari skor: 0 → NOT_CHECKED, >= 80 → MATCHED, lainnya → MISMATCH.
Idempoten: db/06 sudah memuat kolom ini untuk pemasangan baru.

Revision ID: v2_0012
Revises: v2_0011
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0012"
down_revision: str | None = "v2_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS face_status VARCHAR(20) NULL")
    op.execute(
        """
        UPDATE attendance
           SET face_status = CASE WHEN face_match_score = 0 THEN 'NOT_CHECKED'
                                  WHEN face_match_score >= 80 THEN 'MATCHED'
                                  ELSE 'MISMATCH' END
         WHERE face_status IS NULL
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE attendance ADD CONSTRAINT ck_attendance_face_status
                CHECK (face_status IN ('MATCHED', 'MISMATCH', 'NOT_CHECKED', 'NOT_ENROLLED', 'SERVICE_DOWN', 'STALE'));
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE attendance DROP CONSTRAINT IF EXISTS ck_attendance_face_status")
    op.execute("ALTER TABLE attendance DROP COLUMN IF EXISTS face_status")
