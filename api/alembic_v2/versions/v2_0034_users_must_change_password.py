"""Kolom `users.must_change_password` (BOOLEAN NOT NULL DEFAULT false): wajib ganti sandi.

Expand: kolom baru dengan default false (PostgreSQL 11+ tanpa menulis ulang tabel); kode lama tidak membacanya.
TRUE saat akun dibuat/di-reset admin; FALSE setelah pengguna mengganti sandinya sendiri.

Revision ID: v2_0034
Revises: v2_0033
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0034"
down_revision: str | None = "v2_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS must_change_password")
