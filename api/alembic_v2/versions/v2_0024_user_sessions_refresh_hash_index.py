"""Indeks `user_sessions.refresh_token_hash` untuk pencarian refresh token.

Expand-only: hanya menambah indeks, tanpa mengubah data atau constraint. Indeks dibuat
`CONCURRENTLY` agar tabel tidak terkunci untuk tulis selama pembuatan.

Tidak `UNIQUE` dan tidak parsial: kueri `AuthSessionRepository.rotate` dan
`revoke_by_refresh_token` mencari hash tanpa filter `delete_at` (deteksi pemakaian ulang
butuh baris yang sudah dicabut atau dihapus), sehingga indeks parsial tidak dipakai.

Kueri pendukung: `SELECT ... FROM user_sessions s WHERE s.refresh_token_hash = :hash`
(api/app/modules/auth/repositories/auth_session_repository.py, rotate).

Revision ID: v2_0024
Revises: v2_0023
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0024"
down_revision: str | None = "v2_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_sessions_refresh_token_hash "
            "ON user_sessions (refresh_token_hash)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_user_sessions_refresh_token_hash")
