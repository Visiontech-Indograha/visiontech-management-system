"""Tabel penanda popup K3 per hari (`hse_campaign_views`).

Expand-only. CATATAN (utang teknis): fitur "sekali sehari" dibatalkan karena memungkinkan melewati baca wajib
dengan memuat ulang halaman. Tabel ini sudah diterapkan di dev DB dan TIDAK dipakai lagi; sengaja tidak di-drop
(aman dibiarkan). Hapus lewat migrasi terpisah bila sudah tidak diperlukan.

Revision ID: v2_0022
Revises: v2_0021
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0022"
down_revision: str | None = "v2_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS hse_campaign_views (
            campaign_id UUID NOT NULL REFERENCES hse_campaigns(campaign_id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            view_date DATE NOT NULL,
            first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (campaign_id, user_id, view_date)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hse_campaign_views")
