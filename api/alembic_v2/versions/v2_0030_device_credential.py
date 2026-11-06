"""Tabel `device_credential` (kredensial perangkat untuk masuk dengan sidik jari) - hanya expand.

Token perangkat acak 256-bit; basis data hanya menyimpan SHA-256-nya (CHAR(64), unik). Umur 30 hari.
Satu kredensial aktif per (akun, perangkat); rotasi memakai UPDATE bersyarat (`revoked_at IS NULL`) sehingga
dua pemakaian token yang sama serentak hanya satu yang berhasil.

Tanpa RLS, mengikuti `user_sessions` (tabel sesi juga tidak ber-RLS). Tidak mengubah tabel lain.

Indeks dibuat CONCURRENTLY (pola v2_0029); indeks INVALID sisa kegagalan dibuang dulu.

Revision ID: v2_0030
Revises: v2_0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2_0030"
down_revision: str | None = "v2_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UQ_ACTIVE = "uq_device_credential_active"
_IX_USER = "ix_device_credential_user"
_NAMES = [_UQ_ACTIVE, _IX_USER]


def _drop_invalid() -> None:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT c.relname FROM pg_index x JOIN pg_class c ON c.oid = x.indexrelid "
            "WHERE NOT x.indisvalid AND c.relname = ANY(:n)"
        ),
        {"n": _NAMES},
    )
    for (name,) in rows.fetchall():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS device_credential (
            credential_id UUID PRIMARY KEY DEFAULT uuidv7(),
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            device_name VARCHAR(100) NOT NULL,
            token_hash CHAR(64) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            last_used_at TIMESTAMPTZ NULL,
            revoked_at TIMESTAMPTZ NULL,
            revoked_reason VARCHAR(30) NULL,
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            delete_at TIMESTAMPTZ NULL,
            CONSTRAINT uq_device_credential_token_hash UNIQUE (token_hash)
        )
        """
    )
    with op.get_context().autocommit_block():
        _drop_invalid()
        op.execute(
            f"CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {_UQ_ACTIVE} ON device_credential "
            "(user_id, device_name) WHERE revoked_at IS NULL AND delete_at IS NULL"
        )
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_IX_USER} ON device_credential (user_id) "
            "WHERE delete_at IS NULL"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name in _NAMES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")
    op.execute("DROP TABLE IF EXISTS device_credential")
