"""Alur SK v2 PR2 (flowchart SK2-E): laporan harian berjenjang anggota → ketua → PM.

- `member_daily_report` + `member_report_evidence`: laporan harian tiap anggota untuk ketua (Draf → Dikirim).
- `daily_report.resubmitted`, `weekly_report.resubmitted`: status "Dikirim ulang" setelah PM meminta perbaikan.

Revision ID: 0019_member_daily_report
Revises: 0018_work_plan_flow_v2
Create Date: 2026-10-03
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0019_member_daily_report"
down_revision: str | Sequence[str] | None = "0018_work_plan_flow_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute(
        """
        CREATE TABLE member_daily_report (
          id                uuid PRIMARY KEY DEFAULT new_id(),
          work_plan_day_id  uuid NOT NULL REFERENCES work_plan_day(id) ON DELETE CASCADE,
          employee_id       uuid NOT NULL REFERENCES employee(id),
          status            text NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','SENT')),
          body              text NOT NULL DEFAULT '',
          obstacle          text NOT NULL DEFAULT '',
          sent_at           timestamptz,
          updated_at        timestamptz NOT NULL DEFAULT now(),
          UNIQUE (work_plan_day_id, employee_id),
          CHECK (status <> 'SENT' OR length(btrim(body)) >= 10)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE member_report_evidence (
          member_report_id uuid NOT NULL REFERENCES member_daily_report(id) ON DELETE CASCADE,
          file_id          uuid NOT NULL REFERENCES file_object(id),
          PRIMARY KEY (member_report_id, file_id)
        )
        """
    )
    op.execute("ALTER TABLE daily_report ADD COLUMN resubmitted boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE weekly_report ADD COLUMN resubmitted boolean NOT NULL DEFAULT false")
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_app') THEN
            GRANT SELECT, INSERT, UPDATE ON vms.member_daily_report TO vms_app;
            GRANT SELECT, INSERT, UPDATE, DELETE ON vms.member_report_evidence TO vms_app;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_readonly') THEN
            GRANT SELECT ON vms.member_daily_report, vms.member_report_evidence TO vms_readonly;
          END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute("ALTER TABLE weekly_report DROP COLUMN IF EXISTS resubmitted")
    op.execute("ALTER TABLE daily_report DROP COLUMN IF EXISTS resubmitted")
    op.execute("DROP TABLE IF EXISTS member_report_evidence")
    op.execute("DROP TABLE IF EXISTS member_daily_report")
