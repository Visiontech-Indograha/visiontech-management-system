"""Hapus tabel `hse_campaign_views` (tidak dipakai kode sejak fitur popup sekali sehari dibatalkan).

Tidak ada FK, view, atau trigger yang merujuknya; tidak ada kode yang membaca/menulis. Autodeploy
mencadangkan DB sebelum migrasi. Downgrade membuat ulang struktur persis seperti v2_0022 (data tidak kembali).

Revision ID: v2_0031
Revises: v2_0030
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0031"
down_revision: str | None = "v2_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS hse_campaign_views")


def downgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS hse_campaign_views (
            campaign_id UUID NOT NULL REFERENCES hse_campaigns(campaign_id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            view_date DATE NOT NULL,
            first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (campaign_id, user_id, view_date)
        )
    """)
