"""Move the former V2 startup DDL into the versioned Alembic history.

Revision ID: v2_0002
Revises: v2_0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0002"
down_revision: str | None = "v2_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE image_requirement ADD COLUMN IF NOT EXISTS description TEXT NULL")

    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS division_id UUID REFERENCES division(division_id)")
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS pm_id UUID REFERENCES employee(employee_id)")
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS client_name VARCHAR(150) NOT NULL DEFAULT 'Klien Umum'"
    )
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS project_title "
        "VARCHAR(255) NOT NULL DEFAULT 'Pekerjaan Lapangan'"
    )
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS order_number VARCHAR(50) NULL")
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS total_target_unit INT NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS unit_measure VARCHAR(50) NOT NULL DEFAULT 'Unit'")
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS order_status VARCHAR(30) NOT NULL DEFAULT 'ONGOING'"
    )
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS priority_level VARCHAR(20) NOT NULL DEFAULT 'NORMAL'"
    )
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS site_address TEXT NULL")
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS site_lat NUMERIC(10,7) NULL")
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS site_lng NUMERIC(10,7) NULL")

    for column in (
        "daily_plan_id",
        "leader_signer_id",
        "leader_signature_path",
        "leader_signed_at",
        "signature_hash",
    ):
        op.execute(f"ALTER TABLE work_completion ALTER COLUMN {column} DROP NOT NULL")

    op.execute(
        "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS completion_id "
        "UUID NULL REFERENCES work_completion(completion_id)"
    )
    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS start_time TIME NULL DEFAULT '08:00:00'")
    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS end_time TIME NULL DEFAULT '17:00:00'")
    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS location_name VARCHAR(150) NULL")
    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS site_lat NUMERIC(10,7) NULL")
    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS site_lng NUMERIC(10,7) NULL")
    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS assigned_employee_ids JSONB NULL")

    op.execute(
        "ALTER TABLE document_template_export ADD COLUMN IF NOT EXISTS source_type "
        "VARCHAR(30) NOT NULL DEFAULT 'WORK_COMPLETION'"
    )
    op.execute(
        "ALTER TABLE document_template_export ADD COLUMN IF NOT EXISTS daily_plan_id "
        "UUID NULL REFERENCES work_plan_daily(daily_plan_id)"
    )
    op.execute("ALTER TABLE document_template_export ALTER COLUMN completion_id DROP NOT NULL")

    op.execute("ALTER TABLE vehicle ADD COLUMN IF NOT EXISTS photo_path VARCHAR(255) NULL")
    op.execute("ALTER TABLE tool ADD COLUMN IF NOT EXISTS photo_path VARCHAR(255) NULL")
    op.execute("ALTER TABLE employee ADD COLUMN IF NOT EXISTS photo_path VARCHAR(255) NULL")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_site_visit (
            visit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            attendance_id UUID NOT NULL REFERENCES attendance(attendance_id) ON DELETE CASCADE,
            item_id UUID NOT NULL REFERENCES work_plan_item(item_id),
            check_in_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            visit_lat NUMERIC(10,7) NOT NULL,
            visit_lng NUMERIC(10,7) NOT NULL,
            photo_path VARCHAR(255) NOT NULL,
            distance_to_target_m INT NOT NULL,
            is_within_radius BOOLEAN NOT NULL DEFAULT TRUE,
            notes TEXT NULL,
            create_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_site_visit_attendance ON attendance_site_visit(attendance_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_site_visit_item ON attendance_site_visit(item_id)")

    op.execute("ALTER TABLE work_plan_daily ALTER COLUMN site_name DROP NOT NULL")
    op.execute("ALTER TABLE work_plan_daily ALTER COLUMN site_lat DROP NOT NULL")
    op.execute("ALTER TABLE work_plan_daily ALTER COLUMN site_lng DROP NOT NULL")
    op.execute("ALTER TABLE work_plan_daily ALTER COLUMN attendance_radius_m DROP NOT NULL")

    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS client_id UUID NULL REFERENCES client(client_id)")
    op.execute("ALTER TABLE work_completion ALTER COLUMN client_name DROP NOT NULL")
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_status VARCHAR(30) NOT NULL DEFAULT 'MENUNGGU_ACC'"
    )
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_decided_at TIMESTAMPTZ NULL")
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_decided_by_id "
        "UUID NULL REFERENCES employee(employee_id)"
    )
    op.execute("ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS acc_notes TEXT NULL")

    for name, expression in (
        ("ck_work_completion_acc_status", "acc_status IN ('MENUNGGU_ACC', 'DITERIMA', 'DITOLAK_REWORK')"),
        (
            "ck_work_completion_order_status",
            "order_status IN ('DRAFT', 'PENDING', 'PLANNED', 'ONGOING', 'IN_PROGRESS', "
            "'WAITING_ACC', 'ACCEPTED', 'REWORK', 'COMPLETED', 'CANCELLED', 'URGENT')",
        ),
        ("ck_work_completion_priority", "priority_level IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')"),
    ):
        op.execute(f"ALTER TABLE work_completion DROP CONSTRAINT IF EXISTS {name}")
        op.execute(f"ALTER TABLE work_completion ADD CONSTRAINT {name} CHECK ({expression})")

    op.execute(
        """
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
        )
        """
    )

    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS source_type VARCHAR(30) NOT NULL DEFAULT 'PLAN'")
    op.execute(
        "ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS revision_id "
        "UUID NULL REFERENCES work_completion_revision(revision_id)"
    )
    op.execute("ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS point_status VARCHAR(10) NULL")

    for name, expression in (
        (
            "ck_work_plan_item_status",
            "status IN ('TODO', 'IN_PROGRESS', 'DONE', 'PENDING_ROLLOVER', 'SHIFTED_DAY', 'CANCELLED')",
        ),
        ("ck_work_plan_item_source", "source_type IN ('PLAN', 'CLIENT_REVISION', 'REWORK')"),
        ("ck_work_plan_item_point_status", "point_status IS NULL OR point_status IN ('EXISTING', 'PROPOSED')"),
    ):
        op.execute(f"ALTER TABLE work_plan_item DROP CONSTRAINT IF EXISTS {name}")
        op.execute(f"ALTER TABLE work_plan_item ADD CONSTRAINT {name} CHECK ({expression})")

    op.execute("ALTER TABLE work_plan_item DROP CONSTRAINT IF EXISTS fk_work_plan_item_completion")
    op.execute(
        "ALTER TABLE work_plan_item ADD CONSTRAINT fk_work_plan_item_completion "
        "FOREIGN KEY (completion_id) REFERENCES work_completion(completion_id) ON DELETE SET NULL"
    )

    op.execute(
        """
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
        )
        """
    )

    for index_sql in (
        "CREATE INDEX IF NOT EXISTS idx_revision_completion "
        "ON work_completion_revision(completion_id) WHERE delete_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_daily_report_plan "
        "ON work_plan_daily_report(daily_plan_id) WHERE delete_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_daily_report_leader "
        "ON work_plan_daily_report(leader_employee_id) WHERE delete_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_item_completion_id ON work_plan_item(completion_id) WHERE delete_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_item_depends_on ON work_plan_item(depends_on_item_id) WHERE delete_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_item_origin ON work_plan_item(origin_item_id) WHERE delete_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_item_shifted_to ON work_plan_item(shifted_to_daily_id) WHERE delete_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_daily_project_id ON work_plan_daily(project_id) WHERE delete_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_completion_project_id ON work_completion(project_id) WHERE delete_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_completion_client_id ON work_completion(client_id) WHERE delete_at IS NULL",
    ):
        op.execute(index_sql)

    op.execute("ALTER TABLE work_type ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'WORK'")
    op.execute("ALTER TABLE work_type DROP CONSTRAINT IF EXISTS work_type_kind_check")
    op.execute(
        "ALTER TABLE work_type ADD CONSTRAINT work_type_kind_check CHECK "
        "(kind IN ('WORK', 'INSTALLATION', 'SURVEY_TASK', 'SURVEY_POINT', "
        "'MAINTENANCE', 'REPLACEMENT', 'PREPARATION'))"
    )
    op.execute(
        "ALTER TABLE work_type ADD COLUMN IF NOT EXISTS follow_up_work_type_id "
        "UUID NULL REFERENCES work_type(work_type_id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_work_type_division_kind ON work_type(division_id, kind) WHERE delete_at IS NULL"
    )
    op.execute("ALTER TABLE employee ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20) NULL")


def downgrade() -> None:
    raise RuntimeError(
        "V2 schema updates are forward-only because dropping their fields and tables can destroy live data."
    )
