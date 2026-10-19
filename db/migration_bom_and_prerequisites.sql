-- db/migration_bom_and_prerequisites.sql
-- Migrasi Master Template BoM Default 1:N dan Bon Material Proyek Klien VMS V2/V3

-- 1. Tabel work_type_default_materials (Template Material Default per Tipe Pekerjaan)
CREATE TABLE IF NOT EXISTS work_type_default_materials (
    default_material_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_type_id UUID NOT NULL REFERENCES work_type(work_type_id) ON DELETE CASCADE,
    material_code VARCHAR(50) NULL,
    material_name VARCHAR(255) NOT NULL,
    default_qty NUMERIC(10,2) NOT NULL DEFAULT 1.00,
    unit VARCHAR(50) NOT NULL DEFAULT 'Unit',
    category VARCHAR(100) NULL,
    description TEXT NULL,
    sort_order SMALLINT NOT NULL DEFAULT 0,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_wt_default_materials_type ON work_type_default_materials (work_type_id) WHERE delete_at IS NULL;

-- 2. Tabel work_completion_bom (Bon Material Riil Proyek / Order Klien)
CREATE TABLE IF NOT EXISTS work_completion_bom (
    bom_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    completion_id UUID NOT NULL REFERENCES work_completion(completion_id) ON DELETE CASCADE,
    work_plan_item_id UUID NULL REFERENCES work_plan_item(item_id) ON DELETE SET NULL,
    material_code VARCHAR(50) NULL,
    material_name VARCHAR(255) NOT NULL,
    estimated_qty NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    actual_qty NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    unit VARCHAR(50) NOT NULL DEFAULT 'Unit',
    category VARCHAR(100) NULL,
    notes TEXT NULL,
    sort_order SMALLINT NOT NULL DEFAULT 0,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_wc_bom_completion ON work_completion_bom (completion_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_wc_bom_item ON work_completion_bom (work_plan_item_id) WHERE delete_at IS NULL;
