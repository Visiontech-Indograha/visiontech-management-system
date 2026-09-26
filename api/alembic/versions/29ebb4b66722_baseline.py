"""baseline

Revision ID: 29ebb4b66722
Revises: 
Create Date: 2026-09-23 12:08:04.203607

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '29ebb4b66722'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
