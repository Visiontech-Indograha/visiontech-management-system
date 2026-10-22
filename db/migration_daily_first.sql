-- db/migration_daily_first.sql
-- Migrasi Transaksi Arsitektur Daily-First (Zero Data Loss)
-- Mengeliminasi work_plan_weekly dan menaikkan work_plan_daily sebagai entitas induk

BEGIN;

-- 1. Tambahkan kolom relasi organisasi dan approval ke work_plan_daily
ALTER TABLE work_plan_daily
    ADD COLUMN IF NOT EXISTS division_id UUID NULL REFERENCES division(division_id),
    ADD COLUMN IF NOT EXISTS team_id UUID NULL REFERENCES team(team_id),
    ADD COLUMN IF NOT EXISTS created_by_id UUID NULL REFERENCES employee(employee_id),
    ADD COLUMN IF NOT EXISTS approved_by_pm_id UUID NULL REFERENCES employee(employee_id),
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS rejection_reason TEXT NULL;

-- 2. Salin data relasi yang sudah ada dari work_plan_weekly ke work_plan_daily
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'work_plan_weekly'
    ) THEN
        UPDATE work_plan_daily wpd
        SET 
            division_id = wpw.division_id,
            team_id = wpw.team_id,
            created_by_id = wpw.created_by_id,
            approved_by_pm_id = wpw.approved_by_pm_id,
            approved_at = CASE WHEN wpw.status = 'APPROVED' THEN wpw.update_at ELSE NULL END
        FROM work_plan_weekly wpw
        WHERE wpd.weekly_plan_id = wpw.weekly_plan_id;
    END IF;
END $$;

-- 3. Fallback jika ada baris daily tanpa weekly (ambil default dari division/team pertama)
UPDATE work_plan_daily 
SET division_id = (SELECT division_id FROM division WHERE delete_at IS NULL LIMIT 1)
WHERE division_id IS NULL;

UPDATE work_plan_daily 
SET team_id = (SELECT team_id FROM team WHERE delete_at IS NULL LIMIT 1)
WHERE team_id IS NULL;

UPDATE work_plan_daily 
SET created_by_id = (SELECT employee_id FROM employee WHERE delete_at IS NULL LIMIT 1)
WHERE created_by_id IS NULL;

-- 4. Kunci kolom division_id, team_id, created_by_id menjadi NOT NULL
ALTER TABLE work_plan_daily
    ALTER COLUMN division_id SET NOT NULL,
    ALTER COLUMN team_id SET NOT NULL,
    ALTER COLUMN created_by_id SET NOT NULL;

-- 5. Tambahkan kolom fase kerja, deliverable utama, prasyarat, dan foto realisasi ke work_plan_item
ALTER TABLE work_plan_item
    ADD COLUMN IF NOT EXISTS task_phase VARCHAR(30) NOT NULL DEFAULT 'MAIN_INSTALLATION',
    ADD COLUMN IF NOT EXISTS is_main_deliverable BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS depends_on_item_id UUID NULL REFERENCES work_plan_item(item_id),
    ADD COLUMN IF NOT EXISTS realization_photos_json JSONB NOT NULL DEFAULT '[]'::jsonb;

-- 6. Tambahkan rentang tanggal kerja riil ke work_completion & document_template_export
ALTER TABLE work_completion
    ADD COLUMN IF NOT EXISTS start_work_date DATE NULL,
    ADD COLUMN IF NOT EXISTS end_work_date DATE NULL;

ALTER TABLE document_template_export
    ADD COLUMN IF NOT EXISTS period_start_date DATE NULL,
    ADD COLUMN IF NOT EXISTS period_end_date DATE NULL;

-- 7. Lepaskan ketergantungan kolom weekly_plan_id dan allocated_to_weekly_id dari semua tabel
ALTER TABLE work_plan_item 
    DROP COLUMN IF EXISTS weekly_plan_id,
    DROP COLUMN IF EXISTS allocated_to_weekly_id;

ALTER TABLE work_completion 
    DROP COLUMN IF EXISTS weekly_plan_id;

ALTER TABLE document_template_export 
    DROP COLUMN IF EXISTS weekly_plan_id;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'company_mess_stay'
    ) THEN
        ALTER TABLE company_mess_stay DROP COLUMN IF EXISTS weekly_plan_id;
    END IF;
END $$;

ALTER TABLE work_plan_daily 
    DROP COLUMN IF EXISTS weekly_plan_id;

-- 8. Hapus tabel work_plan_weekly secara permanen
DROP TABLE IF EXISTS work_plan_weekly CASCADE;

-- 9. Buat composite index untuk pencarian dan filter cepat
CREATE INDEX IF NOT EXISTS idx_daily_plan_filter 
ON work_plan_daily (work_date, division_id, team_id) 
WHERE delete_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_plan_item_completion 
ON work_plan_item (completion_id) 
WHERE delete_at IS NULL;

COMMIT;
