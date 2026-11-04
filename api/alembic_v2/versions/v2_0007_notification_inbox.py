"""Kotak masuk notifikasi: notifikasi tersimpan (tidak hilang saat pengguna offline).

Revision ID: v2_0007
Revises: v2_0006
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0007"
down_revision: str | None = "v2_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification (
            notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            kind VARCHAR(40) NOT NULL,
            title VARCHAR(200) NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            daily_plan_id UUID NULL,
            target VARCHAR(40) NULL,
            read_at TIMESTAMPTZ NULL,
            create_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_notification_user_created ON notification (user_id, create_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notification_user_unread ON notification (user_id) WHERE read_at IS NULL")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification")
