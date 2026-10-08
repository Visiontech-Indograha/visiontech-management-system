"""Riwayat revisi rencana kerja oleh PM (Rencana Kerja v3, T6, 2026-10-08).

Revision ID: 0027_plan_revision
Revises: 0026_rencana_kerja_rules
Create Date: 2026-10-08

Satu baris per revisi: siapa, kapan, alasan, dan diff sebelum/sesudah. Insert-only (tanpa UPDATE/DELETE untuk
`vms_api`) sehingga riwayat tidak dapat diubah. Pagar RLS tenant seperti 0025.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0027_plan_revision"
down_revision: str | None = "0026_rencana_kerja_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vms.plan_revision (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id    uuid NOT NULL REFERENCES vms.organization(id) ON DELETE CASCADE,
            work_plan_id       uuid NOT NULL REFERENCES vms.work_plan(id) ON DELETE CASCADE,
            revision           integer NOT NULL,
            revised_by         uuid REFERENCES vms.employee(id),
            reason             text NOT NULL,
            diff               jsonb NOT NULL,
            resolved_change_id uuid REFERENCES vms.plan_change(id),
            created_at         timestamptz NOT NULL DEFAULT now(),
            UNIQUE (work_plan_id, revision)
        )
        """
    )
    op.execute("CREATE INDEX ix_plan_revision_organization_id ON vms.plan_revision (organization_id)")
    op.execute("CREATE INDEX ix_plan_revision_revised_by ON vms.plan_revision (revised_by)")
    op.execute("CREATE INDEX ix_plan_revision_resolved_change_id ON vms.plan_revision (resolved_change_id)")
    op.execute("GRANT SELECT, INSERT ON vms.plan_revision TO vms_api")
    op.execute("ALTER TABLE vms.plan_revision ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY plan_revision_isolation ON vms.plan_revision "
               "USING (organization_id = vms.current_org_id())")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vms.plan_revision")
