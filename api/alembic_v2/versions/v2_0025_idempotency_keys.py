"""Tabel `idempotency_keys` untuk Idempotency-Key opsional (F-03, docs/06 Idempotensi).

Expand-only: tabel baru tanpa menyentuh data lama. Tanpa header Idempotency-Key, tabel ini tidak
pernah disentuh (perilaku lama tetap). Hanya operasi yang sudah selesai yang disimpan, di dalam
transaksi yang sama dengan aksinya; sisanya ditangani kunci advisory transaksi.

Indeks `created_at` dibuat CONCURRENTLY untuk pembersihan (`cleanup-idempotency`).

Revision ID: v2_0025
Revises: v2_0024
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0025"
down_revision: str | None = "v2_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            idempotency_key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            key VARCHAR(128) NOT NULL,
            request_hash CHAR(64) NOT NULL,
            status SMALLINT NOT NULL CHECK (status BETWEEN 100 AND 599),
            response_body JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_idempotency_keys_scope UNIQUE (organization_id, user_id, key)
        )
        """
    )
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_idempotency_keys_created_at "
            "ON idempotency_keys (created_at)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_idempotency_keys_created_at")
    op.execute("DROP TABLE IF EXISTS idempotency_keys")
