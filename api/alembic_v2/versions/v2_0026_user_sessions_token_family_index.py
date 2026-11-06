"""Indeks `user_sessions.token_family_id` untuk subquery rotasi refresh token.

Expand-only: hanya menambah indeks, tanpa mengubah data atau constraint. Indeks dibuat
`CONCURRENTLY` agar tabel tidak terkunci untuk tulis selama pembuatan.

Tidak `UNIQUE` dan tidak parsial: subquery `AuthSessionRepository.rotate`
(`min(create_at) ... WHERE f.token_family_id = s.token_family_id`) dan `UPDATE ... WHERE
token_family_id = :fid` tidak memfilter `delete_at`, sehingga indeks parsial tidak dipakai.
Tanpa indeks ini, setiap rotasi memindai seluruh `user_sessions` (Seq Scan).

Revision ID: v2_0026
Revises: v2_0025
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0026"
down_revision: str | None = "v2_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_sessions_token_family_id "
            "ON user_sessions (token_family_id)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_user_sessions_token_family_id")
