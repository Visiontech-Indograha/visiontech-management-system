"""Peleburan projects & work_completion ke client_work_orders, client_sites, dan work_order_items.

Revolusi alur kerja VMS V2:
1. Tabel `client_sites` untuk cabang/lokasi klien lengkap dengan koordinat & radius absen.
2. Kolom `photo_requirements` dan `default_bom` langsung di `work_type`.
3. Tabel `client_work_orders` dengan State Machine 8 status.
4. Tabel `work_order_surveys` & `work_order_survey_points` (rekomendasi work type & BOM).
5. Tabel `work_order_items` & `work_order_bom` (hasil persetujuan survei oleh PM).
6. Kolom `work_order_id` & `work_order_item_id` pada `work_plan_item`.

Revision ID: v2_0018
Revises: v2_0017
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0018"
down_revision: str | None = "v2_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Tabel client_sites
    op.execute("""
    CREATE TABLE IF NOT EXISTS client_sites (
        site_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        client_id UUID NOT NULL REFERENCES client(client_id) ON DELETE CASCADE,
        site_name VARCHAR(150) NOT NULL,
        address TEXT NOT NULL,
        latitude NUMERIC(10, 7) NOT NULL,
        longitude NUMERIC(10, 7) NOT NULL,
        geofence_radius_meters INTEGER NOT NULL DEFAULT 100,
        pic_name VARCHAR(120),
        pic_phone VARCHAR(30),
        create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        delete_at TIMESTAMPTZ NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_client_sites_client ON client_sites(client_id) WHERE delete_at IS NULL")

    # 2. Kolom JSONB di work_type
    op.execute("ALTER TABLE work_type ADD COLUMN IF NOT EXISTS photo_requirements JSONB NOT NULL DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE work_type ADD COLUMN IF NOT EXISTS default_bom JSONB NOT NULL DEFAULT '[]'::jsonb")

    # 3. Tabel client_work_orders
    op.execute("""
    CREATE TABLE IF NOT EXISTS client_work_orders (
        work_order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        wo_number VARCHAR(60) NOT NULL UNIQUE,
        client_id UUID NOT NULL REFERENCES client(client_id) ON DELETE RESTRICT,
        client_site_id UUID REFERENCES client_sites(site_id) ON DELETE SET NULL,
        division_id UUID NOT NULL REFERENCES division(division_id) ON DELETE RESTRICT,
        pm_id UUID NOT NULL REFERENCES employee(employee_id) ON DELETE RESTRICT,
        lead_team_id UUID REFERENCES team(team_id) ON DELETE SET NULL,
        title VARCHAR(200) NOT NULL,
        initial_complaint TEXT,
        status VARCHAR(40) NOT NULL DEFAULT 'WAITING_SURVEY'
            CHECK (status IN (
                'WAITING_SURVEY', 'SURVEY_IN_PROGRESS', 'SURVEY_SUBMITTED',
                'READY_TO_EXECUTE', 'IN_PROGRESS', 'COMPLETED', 'BAST_SIGNED', 'CANCELLED'
            )),
        survey_assigned_at TIMESTAMPTZ,
        survey_submitted_at TIMESTAMPTZ,
        survey_approved_at TIMESTAMPTZ,
        survey_approved_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
        bast_signed_at TIMESTAMPTZ,
        bast_signer_name VARCHAR(120),
        bast_signature_file_id UUID REFERENCES file_object(id) ON DELETE SET NULL,
        verify_hash VARCHAR(128),
        create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        delete_at TIMESTAMPTZ NULL
    )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cwo_division_status
        ON client_work_orders(division_id, status) WHERE delete_at IS NULL
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cwo_client ON client_work_orders(client_id) WHERE delete_at IS NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cwo_team ON client_work_orders(lead_team_id) WHERE delete_at IS NULL")

    # 4. Tabel work_order_surveys
    op.execute("""
    CREATE TABLE IF NOT EXISTS work_order_surveys (
        survey_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        work_order_id UUID NOT NULL REFERENCES client_work_orders(work_order_id) ON DELETE CASCADE,
        surveyor_team_id UUID REFERENCES team(team_id) ON DELETE SET NULL,
        survey_date DATE NOT NULL DEFAULT CURRENT_DATE,
        narrative TEXT,
        general_bom JSONB NOT NULL DEFAULT '[]'::jsonb,
        format VARCHAR(20) NOT NULL DEFAULT 'CCTV',
        status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
        submitted_at TIMESTAMPTZ,
        approved_at TIMESTAMPTZ,
        approved_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
        create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        delete_at TIMESTAMPTZ NULL
    )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_wo_surveys_wo ON work_order_surveys(work_order_id) WHERE delete_at IS NULL"
    )

    # 5. Tabel work_order_survey_points
    op.execute("""
    CREATE TABLE IF NOT EXISTS work_order_survey_points (
        point_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        work_order_id UUID NOT NULL REFERENCES client_work_orders(work_order_id) ON DELETE CASCADE,
        survey_id UUID REFERENCES work_order_surveys(survey_id) ON DELETE CASCADE,
        point_name VARCHAR(150) NOT NULL,
        location_detail TEXT,
        site_lat NUMERIC(10, 7),
        site_lng NUMERIC(10, 7),
        recommended_work_type_id UUID REFERENCES work_type(work_type_id) ON DELETE RESTRICT,
        recommended_bom JSONB NOT NULL DEFAULT '[]'::jsonb,
        remarks TEXT,
        photos_json JSONB NOT NULL DEFAULT '[]'::jsonb,
        status VARCHAR(30) NOT NULL DEFAULT 'TODO',
        create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        delete_at TIMESTAMPTZ NULL
    )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_wo_survey_points_wo
        ON work_order_survey_points(work_order_id) WHERE delete_at IS NULL
    """)

    # 6. Tabel work_order_items
    op.execute("""
    CREATE TABLE IF NOT EXISTS work_order_items (
        item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        work_order_id UUID NOT NULL REFERENCES client_work_orders(work_order_id) ON DELETE CASCADE,
        survey_point_id UUID REFERENCES work_order_survey_points(point_id) ON DELETE SET NULL,
        work_type_id UUID NOT NULL REFERENCES work_type(work_type_id) ON DELETE RESTRICT,
        title VARCHAR(200) NOT NULL,
        location_detail TEXT,
        target_qty NUMERIC(10, 2) NOT NULL DEFAULT 1,
        completed_qty NUMERIC(10, 2) NOT NULL DEFAULT 0,
        photo_slots_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,
        status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
            CHECK (status IN ('PENDING', 'IN_PROGRESS', 'DONE')),
        create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        delete_at TIMESTAMPTZ NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_wo_items_wo ON work_order_items(work_order_id) WHERE delete_at IS NULL")

    # 7. Tabel work_order_bom
    op.execute("""
    CREATE TABLE IF NOT EXISTS work_order_bom (
        bom_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        work_order_id UUID NOT NULL REFERENCES client_work_orders(work_order_id) ON DELETE CASCADE,
        work_order_item_id UUID REFERENCES work_order_items(item_id) ON DELETE CASCADE,
        item_name VARCHAR(150) NOT NULL,
        unit VARCHAR(30) NOT NULL DEFAULT 'pcs',
        estimated_qty NUMERIC(10, 2) NOT NULL DEFAULT 0,
        actual_qty NUMERIC(10, 2) NOT NULL DEFAULT 0,
        create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        delete_at TIMESTAMPTZ NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_wo_bom_wo ON work_order_bom(work_order_id) WHERE delete_at IS NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_wo_bom_item ON work_order_bom(work_order_item_id) WHERE delete_at IS NULL"
    )

    # 8. Kolom relasi di work_plan_item
    op.execute("""
        ALTER TABLE work_plan_item
        ADD COLUMN IF NOT EXISTS work_order_id UUID
        REFERENCES client_work_orders(work_order_id) ON DELETE SET NULL
    """)
    op.execute("""
        ALTER TABLE work_plan_item
        ADD COLUMN IF NOT EXISTS work_order_item_id UUID
        REFERENCES work_order_items(item_id) ON DELETE SET NULL
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_work_plan_item_wo ON work_plan_item(work_order_id) WHERE delete_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_work_plan_item_wo")
    op.execute("ALTER TABLE work_plan_item DROP COLUMN IF EXISTS work_order_item_id")
    op.execute("ALTER TABLE work_plan_item DROP COLUMN IF EXISTS work_order_id")
    op.execute("DROP TABLE IF EXISTS work_order_bom CASCADE")
    op.execute("DROP TABLE IF EXISTS work_order_items CASCADE")
    op.execute("DROP TABLE IF EXISTS work_order_survey_points CASCADE")
    op.execute("DROP TABLE IF EXISTS work_order_surveys CASCADE")
    op.execute("DROP TABLE IF EXISTS client_work_orders CASCADE")
    op.execute("ALTER TABLE work_type DROP COLUMN IF EXISTS default_bom")
    op.execute("ALTER TABLE work_type DROP COLUMN IF EXISTS photo_requirements")
    op.execute("DROP TABLE IF EXISTS client_sites CASCADE")
