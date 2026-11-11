"""hse campaign office id column and index

Revision ID: v2_0040
Revises: v2_0039
Create Date: 2026-11-12 01:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'v2_0040'
down_revision = 'v2_0039'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add office_id nullable column to hse_campaign
    op.add_column(
        'hse_campaign',
        sa.Column('office_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_hse_campaign_office_id',
        'hse_campaign', 'office',
        ['office_id'], ['id'],
        ondelete='SET NULL'
    )

    # 2. Add composite index (organization_id, office_id) IF NOT EXISTS
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_hse_campaign_org_office ON hse_campaign (organization_id, office_id);'
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_hse_campaign_org_office;')
    op.drop_constraint('fk_hse_campaign_office_id', 'hse_campaign', type_='foreignkey')
    op.drop_column('hse_campaign', 'office_id')
