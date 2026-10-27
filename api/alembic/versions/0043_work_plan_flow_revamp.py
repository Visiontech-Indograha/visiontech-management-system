"""Alur Work Plan V2: site nullable, status ACC client, revisi pekerjaan, laporan harian aktif, dan indeks efisiensi.

Revision ID: 0043_work_plan_flow_revamp
Revises: 0042_session_definer
Create Date: 2026-10-26
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0043_work_plan_flow_revamp"
down_revision: str | None = "0042_session_definer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. work_plan_daily: site_name/lat/lng dan attendance_radius_m menjadi nullable
    op.execute("ALTER TABLE work_plan_daily ALTER COLUMN site_name DROP NOT NULL;")
    op.execute("ALTER TABLE work_plan_daily ALTER COLUMN site_lat DROP NOT NULL;")
    op.execute("ALTER TABLE work_plan_daily ALTER COLUMN site_lng DROP NOT NULL;")
    op.execute("ALTER TABLE work_plan_daily ALTER COLUMN attendance_radius_m DROP NOT NULL;")

    # 2. work_completion: client_id FK, status ACC client, dan CHECK constraints
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS client_id UUID NULL REFERENCES client(client_id);"
    )
    op.execute("ALTER TABLE work_completion ALTER COLUMN client_name DROP NOT NULL;")
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_status VARCHAR(30) NOT NULL DEFAULT 'MENUNGGU_ACC';"
    )
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_decided_at TIMESTAMPTZ NULL;")
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_decided_by_id UUID NULL "
        "REFERENCES employee(employee_id);"
    )
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_notes TEXT NULL;")

    op.execute("ALTER TABLE work_completion DROP CONSTRAINT IF EXISTS ck_work_completion_acc_status;")
    op.execute(
        "ALTER TABLE work_completion ADD CONSTRAINT ck_work_completion_acc_status "
        "CHECK (acc_status IN ('MENUNGGU_ACC', 'DITERIMA', 'DITOLAK_REWORK'));"
    )

    op.execute("ALTER TABLE work_completion DROP CONSTRAINT IF EXISTS ck_work_completion_order_status;")
    op.execute(
        "ALTER TABLE work_completion ADD CONSTRAINT ck_work_completion_order_status "
        "CHECK (order_status IN ('DRAFT', 'PENDING', 'PLANNED', 'ONGOING', 'IN_PROGRESS', "
        "'WAITING_ACC', 'ACCEPTED', 'REWORK', 'COMPLETED', 'CANCELLED', 'URGENT'));"
    )

    op.execute("ALTER TABLE work_completion DROP CONSTRAINT IF EXISTS ck_work_completion_priority;")
    op.execute(
        "ALTER TABLE work_completion ADD CONSTRAINT ck_work_completion_priority "
        "CHECK (priority_level IN ('LOW', 'NORMAL', 'HIGH', 'URGENT'));"
    )

    # 3. work_type: dukung peran/kind 'PREPARATION'
    op.execute("ALTER TABLE work_type DROP CONSTRAINT IF EXISTS work_type_kind_check;")
    op.execute(
        "ALTER TABLE work_type ADD CONSTRAINT work_type_kind_check "
        "CHECK (kind IN ('WORK', 'INSTALLATION', 'SURVEY_TASK', 'SURVEY_POINT', 'MAINTENANCE', "
        "'REPLACEMENT', 'PREPARATION'));"
    )

    # 4. work_completion_revision: tabel revisi permintaan client
    op.execute("""
    CREATE TABLE IF NOT EXISTS work_completion_revision (
        revision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        completion_id UUID NOT NULL REFERENCES work_completion(completion_id) ON DELETE CASCADE,
        description TEXT NOT NULL,
        request_date DATE NOT NULL DEFAULT CURRENT_DATE,
        survey_task_id UUID NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
            CONSTRAINT ck_revision_status CHECK (
                status IN ('PENDING', 'SURVEY_CREATED', 'SCHEDULED', 'COMPLETED', 'CANCELLED')
            ),
        created_by_id UUID NOT NULL REFERENCES employee(employee_id),
        create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        delete_at TIMESTAMPTZ NULL
    );
    """)

    # 5. work_plan_item: status check, source_type, revision_id, dan completion_id FK
    op.execute("ALTER TABLE work_plan_item DROP CONSTRAINT IF EXISTS ck_work_plan_item_status;")
    op.execute(
        "ALTER TABLE work_plan_item ADD CONSTRAINT ck_work_plan_item_status "
        "CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE', 'PENDING_ROLLOVER', 'SHIFTED_DAY', 'CANCELLED'));"
    )

    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'PLAN';")
    op.execute(
        "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS revision_id UUID NULL "
        "REFERENCES work_completion_revision(revision_id);"
    )

    op.execute("ALTER TABLE work_plan_item DROP CONSTRAINT IF EXISTS ck_work_plan_item_source;")
    op.execute(
        "ALTER TABLE work_plan_item ADD CONSTRAINT ck_work_plan_item_source "
        "CHECK (source_type IN ('PLAN', 'CLIENT_REVISION', 'REWORK'));"
    )

    op.execute("ALTER TABLE work_plan_item DROP CONSTRAINT IF EXISTS fk_work_plan_item_completion;")
    op.execute(
        "ALTER TABLE work_plan_item ADD CONSTRAINT fk_work_plan_item_completion "
        "FOREIGN KEY (completion_id) REFERENCES work_completion(completion_id) ON DELETE SET NULL;"
    )

    # 6. work_plan_daily_report: laporan harian aktif per jadwal tim
    op.execute("""
    CREATE TABLE IF NOT EXISTS work_plan_daily_report (
        report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        daily_plan_id UUID NOT NULL UNIQUE REFERENCES work_plan_daily(daily_plan_id) ON DELETE CASCADE,
        leader_employee_id UUID NOT NULL REFERENCES employee(employee_id),
        summary TEXT NOT NULL,
        obstacles TEXT NULL,
        photos_json JSONB NOT NULL DEFAULT '[]'::jsonb,
        submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        delete_at TIMESTAMPTZ NULL
    );
    """)

    # 7. Indeks Efisiensi
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_revision_completion "
        "ON work_completion_revision(completion_id) WHERE delete_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_report_plan "
        "ON work_plan_daily_report(daily_plan_id) WHERE delete_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_report_leader "
        "ON work_plan_daily_report(leader_employee_id) WHERE delete_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_item_completion_id ON work_plan_item(completion_id) WHERE delete_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_item_depends_on ON work_plan_item(depends_on_item_id) WHERE delete_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_item_origin ON work_plan_item(origin_item_id) WHERE delete_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_item_shifted_to ON work_plan_item(shifted_to_daily_id) WHERE delete_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_project_id ON work_plan_daily(project_id) WHERE delete_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_completion_project_id ON work_completion(project_id) WHERE delete_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_completion_client_id ON work_completion(client_id) WHERE delete_at IS NULL;"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS work_plan_daily_report CASCADE;")
    op.execute("DROP TABLE IF EXISTS work_completion_revision CASCADE;")
    op.execute("ALTER TABLE work_plan_item DROP COLUMN IF EXISTS revision_id;")
    op.execute("ALTER TABLE work_plan_item DROP COLUMN IF EXISTS source_type;")
    op.execute("ALTER TABLE work_completion DROP COLUMN IF EXISTS acc_notes;")
    op.execute("ALTER TABLE work_completion DROP COLUMN IF EXISTS acc_decided_by_id;")
    op.execute("ALTER TABLE work_completion DROP COLUMN IF EXISTS acc_decided_at;")
    op.execute("ALTER TABLE work_completion DROP COLUMN IF EXISTS acc_status;")
    op.execute("ALTER TABLE work_completion DROP COLUMN IF EXISTS client_id;")
