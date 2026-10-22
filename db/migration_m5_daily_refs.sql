-- db/migration_m5_daily_refs.sql
-- Milestone 5 (daily-first, keputusan pemilik 2026-10-20): rujukan yang masih menunjuk ke "rencana mingguan"
-- dipindah ke work_plan_daily dengan FK, tabel berkas diformalkan, dan status/fase dibakukan.
-- Idempoten: aman dijalankan ulang. Disamakan dengan db/06_master_schema_v2.sql & .agents/rules/01.

BEGIN;

-- 1. overtime.weekly_plan_id (yatim, tanpa FK) → daily_plan_id FK work_plan_daily (nullable: lembur non-jadwal)
ALTER TABLE overtime ADD COLUMN IF NOT EXISTS daily_plan_id UUID NULL REFERENCES work_plan_daily(daily_plan_id);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'overtime' AND column_name = 'weekly_plan_id') THEN
        -- Nilai lama yang kebetulan id jadwal harian dipertahankan; selebihnya tidak punya padanan.
        UPDATE overtime o SET daily_plan_id = o.weekly_plan_id
        WHERE o.daily_plan_id IS NULL
          AND EXISTS (SELECT 1 FROM work_plan_daily d WHERE d.daily_plan_id = o.weekly_plan_id);
        ALTER TABLE overtime DROP COLUMN weekly_plan_id;
    END IF;
END $$;
DROP INDEX IF EXISTS idx_overtime_weekly_plan;
CREATE INDEX IF NOT EXISTS idx_overtime_daily_plan ON overtime (daily_plan_id);

-- 2. file_object: organization_id → office_id FK office; uploaded_by FK users
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'file_object' AND column_name = 'organization_id') THEN
        ALTER TABLE file_object RENAME COLUMN organization_id TO office_id;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_file_object_office') THEN
        ALTER TABLE file_object ADD CONSTRAINT fk_file_object_office FOREIGN KEY (office_id) REFERENCES office(office_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_file_object_uploader') THEN
        UPDATE file_object f SET uploaded_by = NULL
        WHERE uploaded_by IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.user_id = f.uploaded_by);
        ALTER TABLE file_object ADD CONSTRAINT fk_file_object_uploader FOREIGN KEY (uploaded_by) REFERENCES users(user_id);
    END IF;
END $$;
DROP INDEX IF EXISTS idx_file_object_org_hash;  -- sudah tercakup UNIQUE (office_id, sha256)

-- 3. work_plan_attachment.work_plan_id → daily_plan_id FK work_plan_daily (lampiran jadwal harian)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'work_plan_attachment' AND column_name = 'work_plan_id') THEN
        DELETE FROM work_plan_attachment a
        WHERE NOT EXISTS (SELECT 1 FROM work_plan_daily d WHERE d.daily_plan_id = a.work_plan_id);
        ALTER TABLE work_plan_attachment RENAME COLUMN work_plan_id TO daily_plan_id;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_work_plan_attachment_daily') THEN
        ALTER TABLE work_plan_attachment ADD CONSTRAINT fk_work_plan_attachment_daily
            FOREIGN KEY (daily_plan_id) REFERENCES work_plan_daily(daily_plan_id) ON DELETE CASCADE;
    END IF;
END $$;
DROP INDEX IF EXISTS idx_work_plan_attachment_plan;
CREATE INDEX IF NOT EXISTS idx_work_plan_attachment_daily ON work_plan_attachment (daily_plan_id);

-- 4. work_plan_item.notes (remark titik survei, docs/35 §3) + fase baku
ALTER TABLE work_plan_item ADD COLUMN IF NOT EXISTS notes TEXT NULL;
UPDATE work_plan_item SET task_phase = 'INSTALLATION' WHERE task_phase = 'MAIN_INSTALLATION';
UPDATE work_plan_item SET task_phase = 'MAINTENANCE' WHERE task_phase = 'TESTING_COMMISSIONING';
ALTER TABLE work_plan_item ALTER COLUMN task_phase SET DEFAULT 'INSTALLATION';
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_work_plan_item_phase') THEN
        ALTER TABLE work_plan_item ADD CONSTRAINT ck_work_plan_item_phase
            CHECK (task_phase IN ('SURVEY', 'PREPARATION', 'INSTALLATION', 'REPLACEMENT', 'MAINTENANCE'));
    END IF;
END $$;

-- 5. Status jadwal harian: DRAFT → SUBMITTED → APPROVED → ONGOING → COMPLETED (ditolak PM → DRAFT + rejection_reason)
UPDATE work_plan_daily SET status = 'APPROVED' WHERE status = 'SCHEDULED';
ALTER TABLE work_plan_daily ALTER COLUMN status SET DEFAULT 'DRAFT';
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_work_plan_daily_status') THEN
        ALTER TABLE work_plan_daily ADD CONSTRAINT ck_work_plan_daily_status
            CHECK (status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'ONGOING', 'COMPLETED'));
    END IF;
END $$;

COMMIT;
