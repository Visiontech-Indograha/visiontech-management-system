"""Modul HSE (Health, Safety & Environment / HES): Campaign K3, Mandatory Gate & Inspeksi Kendaraan.

Fitur Utama:
1. Penambahan nilai 'HSE' pada enum system_role_enum.
2. Update akun hse@uji-nyata.test menjadi peran HSE.
3. Tabel `hse_campaigns` untuk konten dan kampanye K3 berjadwal dengan durasi cooldown & target audiens.
4. Tabel `hse_campaign_acknowledgments` untuk audit tracking pembaca yang wajib membaca hingga selesai.
5. Tabel `vehicle_safety_inspections` untuk checklist inspeksi harian/mingguan/bulanan dan foto kendaraan.

Revision ID: v2_0019
Revises: v2_0018
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0019"
down_revision: str | None = "v2_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Tambah role HSE ke enum di luar blok transaksi (aman jika sudah ada)
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE system_role_enum ADD VALUE IF NOT EXISTS 'HSE'")

    # 2. Update akun hse@uji-nyata.test ke role HSE
    op.execute("""
        UPDATE users
        SET system_role = 'HSE'
        WHERE email = 'hse@uji-nyata.test'
    """)

    # 3. Tabel hse_campaigns
    op.execute("""
        CREATE TABLE IF NOT EXISTS hse_campaigns (
            campaign_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(255) NOT NULL,
            summary TEXT,
            content_html TEXT NOT NULL,
            media_path VARCHAR(255),
            target_audience VARCHAR(50) NOT NULL DEFAULT 'ALL',
            target_user_ids JSONB,
            is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
            cooldown_seconds INT NOT NULL DEFAULT 5,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_by_id UUID NOT NULL REFERENCES users(user_id),
            create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delete_at TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hse_campaigns_dates
        ON hse_campaigns (is_active, start_date, end_date)
        WHERE delete_at IS NULL
    """)

    # 4. Tabel hse_campaign_acknowledgments
    op.execute("""
        CREATE TABLE IF NOT EXISTS hse_campaign_acknowledgments (
            acknowledgment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            campaign_id UUID NOT NULL REFERENCES hse_campaigns(campaign_id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            platform VARCHAR(50) NOT NULL DEFAULT 'web',
            device_info VARCHAR(255),
            ip_address INET,
            scroll_completed BOOLEAN NOT NULL DEFAULT TRUE,
            read_duration_seconds INT NOT NULL DEFAULT 0,
            acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_hse_campaign_user UNIQUE (campaign_id, user_id)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hse_ack_campaign ON hse_campaign_acknowledgments (campaign_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_hse_ack_user ON hse_campaign_acknowledgments (user_id)
    """)

    # 5. Tabel vehicle_safety_inspections
    op.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_safety_inspections (
            inspection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            vehicle_id UUID NOT NULL REFERENCES vehicle(vehicle_id) ON DELETE CASCADE,
            inspector_id UUID NOT NULL REFERENCES employee(employee_id) ON DELETE CASCADE,
            period_type VARCHAR(50) NOT NULL DEFAULT 'DAILY',
            inspection_date DATE NOT NULL DEFAULT CURRENT_DATE,
            odometer_km INT,
            checklist_json JSONB NOT NULL DEFAULT '{}',
            photos_json JSONB NOT NULL DEFAULT '[]',
            notes TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED',
            verified_by_id UUID REFERENCES users(user_id),
            verified_at TIMESTAMPTZ,
            create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delete_at TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vsi_vehicle_date ON vehicle_safety_inspections (vehicle_id, inspection_date)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vsi_inspector ON vehicle_safety_inspections (inspector_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vehicle_safety_inspections CASCADE")
    op.execute("DROP TABLE IF EXISTS hse_campaign_acknowledgments CASCADE")
    op.execute("DROP TABLE IF EXISTS hse_campaigns CASCADE")
