"""Kolom `users.last_login_at` (nullable): waktu login berhasil terakhir.

Expand: kolom baru nullable, diisi awal dari max(user_sessions.create_at) untuk data lama; kode mengisinya
saat sesi diterbitkan. NULL = belum pernah masuk. Sesi lama dibersihkan cleanup, jadi sesi bukan sumber andal.

Revision ID: v2_0032
Revises: v2_0031
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0032"
down_revision: str | None = "v2_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ NULL")
    op.execute(
        "UPDATE users u SET last_login_at = s.m FROM "
        "(SELECT user_id, max(create_at) AS m FROM user_sessions GROUP BY user_id) s "
        "WHERE s.user_id = u.user_id AND u.last_login_at IS NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_login_at")
