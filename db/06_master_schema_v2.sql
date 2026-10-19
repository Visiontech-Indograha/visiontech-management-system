-- ============================================================================
-- VISIONTECH MANAGEMENT SYSTEM (VMS) - MASTER DDL (POSTGRESQL) V2
-- 26 Tabel Terintegrasi + Soft Delete + Partisi Log Bulanan
-- ============================================================================

BEGIN;

-- Aktifkan ekstensi UUID bawaan PostgreSQL
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- BAGIAN 1: PEMBUATAN TIPE ENUMERASI (ENUM)
-- ============================================================================
DROP TYPE IF EXISTS system_role_enum CASCADE;
CREATE TYPE system_role_enum AS ENUM ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'PROJECT_MANAGER', 'TEAM_LEADER', 'ADMIN_HR_GA', 'EMPLOYEE');

DROP TYPE IF EXISTS client_platform_enum CASCADE;
CREATE TYPE client_platform_enum AS ENUM ('web_react', 'android_flutter', 'system_cron');

DROP TYPE IF EXISTS offboarding_status_enum CASCADE;
CREATE TYPE offboarding_status_enum AS ENUM ('active', 'in_process', 'offboarded');

DROP TYPE IF EXISTS offboarding_reason_enum CASCADE;
CREATE TYPE offboarding_reason_enum AS ENUM ('PKWT_EXPIRED', 'RESIGN', 'TERMINATED', 'RETIRED');

DROP TYPE IF EXISTS doc_status_enum CASCADE;
CREATE TYPE doc_status_enum AS ENUM ('active', 'not_active', 'extended');

DROP TYPE IF EXISTS vehicle_type_enum CASCADE;
CREATE TYPE vehicle_type_enum AS ENUM ('Motorcycle', 'Car', 'Truck');

DROP TYPE IF EXISTS asset_status_enum CASCADE;
CREATE TYPE asset_status_enum AS ENUM ('ready', 'allocated', 'loaned', 'damaged', 'lost', 'pension');

DROP TYPE IF EXISTS vehicle_file_type_enum CASCADE;
CREATE TYPE vehicle_file_type_enum AS ENUM ('STNK', 'BPKB', 'KIR');

DROP TYPE IF EXISTS inspection_type_enum CASCADE;
CREATE TYPE inspection_type_enum AS ENUM ('day', 'month', 'year', 'repair', 'profile');

DROP TYPE IF EXISTS tool_ownership_enum CASCADE;
CREATE TYPE tool_ownership_enum AS ENUM ('PERSONAL_LOAN', 'SHARED_TOOL');

DROP TYPE IF EXISTS tool_category_enum CASCADE;
CREATE TYPE tool_category_enum AS ENUM ('BAJU', 'LAPTOP', 'SEPATU', 'BOR', 'TANGGA', 'LAINNYA');

DROP TYPE IF EXISTS city_zone_enum CASCADE;
CREATE TYPE city_zone_enum AS ENUM ('DALAM_KOTA', 'LUAR_KOTA');

DROP TYPE IF EXISTS rollover_approval_enum CASCADE;
CREATE TYPE rollover_approval_enum AS ENUM ('NONE', 'WAITING_PM', 'APPROVED_BY_PM', 'REJECTED_BY_PM');

DROP TYPE IF EXISTS export_format_enum CASCADE;
CREATE TYPE export_format_enum AS ENUM ('WORD_DOCX', 'PPTX', 'PDF', 'EXCEL_XLSX');

-- ============================================================================
-- BAGIAN 2: DDL TABEL (26 ENTITAS TERINTEGRASI DENGAN SOFT DELETE)
-- ============================================================================

-- 1. Tabel office (Master Kantor Utama & Cabang - Konfirmasi 4A, 5A)
CREATE TABLE IF NOT EXISTS office (
    office_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    is_main_office BOOLEAN NOT NULL DEFAULT FALSE,
    address TEXT NOT NULL,
    latitude NUMERIC(10,7) NOT NULL,
    longitude NUMERIC(10,7) NOT NULL,
    attendance_radius_m INT NOT NULL DEFAULT 100,
    city_boundary_radius_m INT NOT NULL DEFAULT 15000,
    clock_in_time TIME NOT NULL DEFAULT '07:00:00',
    clock_out_time TIME NOT NULL DEFAULT '16:00:00',
    in_city_meal_rate NUMERIC(12,2) NOT NULL DEFAULT 35000.00,
    out_city_meal_rate NUMERIC(12,2) NOT NULL DEFAULT 65000.00,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- Pastikan hanya boleh ada 1 Kantor Utama aktif di seluruh sistem (5A)
CREATE UNIQUE INDEX IF NOT EXISTS uq_single_main_office ON office (is_main_office) WHERE is_main_office = TRUE AND delete_at IS NULL;

-- 2. Tabel employee (CSV #4 Revisi - Konfirmasi 1A)
CREATE TABLE IF NOT EXISTS employee (
    employee_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id UUID NOT NULL REFERENCES office(office_id),
    division_id UUID NULL, -- Di-link lewat ALTER TABLE setelah tabel division dibuat
    full_name VARCHAR(150) NOT NULL,
    employee_no VARCHAR(50) NOT NULL,
    join_date TIMESTAMPTZ NOT NULL,
    pkwt_end_date TIMESTAMPTZ NULL,
    profile_photo_path VARCHAR(255) NULL,
    photo_path VARCHAR(255) NULL,
    face_embedding JSONB NULL, -- Vektor biometrik wajah
    offboarding_status offboarding_status_enum NOT NULL DEFAULT 'active',
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_no_active ON employee (employee_no) WHERE delete_at IS NULL;

-- 3. Tabel users (Konfirmasi 1B: Dipisah dari employee)
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NULL UNIQUE REFERENCES employee(employee_id),
    username VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    system_role system_role_enum NOT NULL DEFAULT 'EMPLOYEE',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_active ON users (email) WHERE delete_at IS NULL;

-- 4. Tabel user_sessions (JWT Hybrid Session untuk React Web & Flutter Android)
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    token_family_id UUID NOT NULL,
    refresh_token_hash CHAR(64) NOT NULL,
    platform client_platform_enum NOT NULL,
    device_name VARCHAR(100) NOT NULL,
    ip_address INET NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 5. Tabel division (CSV #10 Revisi - Konfirmasi 4A, 4B: OM membawahi beberapa PM)
CREATE TABLE IF NOT EXISTS division (
    division_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    om_id UUID NOT NULL REFERENCES employee(employee_id),
    pm_id UUID NOT NULL REFERENCES employee(employee_id),
    name VARCHAR(100) NOT NULL,
    status BOOLEAN NOT NULL DEFAULT TRUE,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_employee_division' AND table_name = 'employee'
    ) THEN
        ALTER TABLE employee ADD CONSTRAINT fk_employee_division FOREIGN KEY (division_id) REFERENCES division(division_id);
    END IF;
END $$;

-- 6. Tabel team (CSV #2 Revisi - Fix typo devision_id & tambah leader_employee_id)
CREATE TABLE IF NOT EXISTS team (
    team_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id UUID NOT NULL REFERENCES office(office_id),
    division_id UUID NOT NULL REFERENCES division(division_id),
    leader_employee_id UUID NOT NULL REFERENCES employee(employee_id),
    name TEXT NOT NULL,
    status BOOLEAN NOT NULL DEFAULT TRUE,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 7. Tabel member (CSV #8 Revisi)
CREATE TABLE IF NOT EXISTS member (
    member_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES team(team_id),
    employee_id UUID NOT NULL REFERENCES employee(employee_id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 8. Tabel address (CSV #3 Revisi - Fix typo addres & verchar, postal_code jadi VARCHAR)
CREATE TABLE IF NOT EXISTS address (
    address_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employee(employee_id),
    address_line VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 9. Tabel employee_file (Surat & Sertifikat Karyawan)
CREATE TABLE IF NOT EXISTS employee_file (
    employee_file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employee(employee_id),
    type VARCHAR(50) NOT NULL, -- 'KTP', 'SIM_A', 'SIM_B', 'SERTIFIKAT_K3', 'PKWT'
    path_file VARCHAR(255) NOT NULL,
    status doc_status_enum NOT NULL DEFAULT 'active',
    active_at TIMESTAMPTZ NOT NULL,
    expired_at TIMESTAMPTZ NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 10. Tabel tool (Konfirmasi 3B: Gabung Alat Pribadi & Umum, Tanpa Tabel Inspeksi)
CREATE TABLE IF NOT EXISTS tool (
    tool_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id UUID NOT NULL REFERENCES office(office_id),
    division_id UUID NULL REFERENCES division(division_id),
    ownership_type tool_ownership_enum NOT NULL,
    category tool_category_enum NOT NULL,
    name VARCHAR(100) NOT NULL,
    tool_code VARCHAR(50) NOT NULL,
    photo_path VARCHAR(255) NULL,
    status asset_status_enum NOT NULL DEFAULT 'ready',
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tool_code_active ON tool (tool_code) WHERE delete_at IS NULL;

-- 11. Tabel vehicle (CSV #9 Revisi - Fix number_plate dari decimal ke VARCHAR)
CREATE TABLE IF NOT EXISTS vehicle (
    vehicle_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    office_id UUID NOT NULL REFERENCES office(office_id),
    division_id UUID NOT NULL REFERENCES division(division_id),
    vehicle_type vehicle_type_enum NOT NULL,
    name TEXT NOT NULL,
    number_plate VARCHAR(20) NOT NULL,
    photo_path VARCHAR(255) NULL,
    status asset_status_enum NOT NULL DEFAULT 'ready',
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_vehicle_plate_active ON vehicle (number_plate) WHERE delete_at IS NULL;

-- 12. Tabel vehicle_file (CSV #6 Revisi - Fix typo vehile_id & uui)
CREATE TABLE IF NOT EXISTS vehicle_file (
    vehicle_file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicle(vehicle_id),
    type vehicle_file_type_enum NOT NULL,
    path_file VARCHAR(255) NOT NULL,
    status doc_status_enum NOT NULL DEFAULT 'active',
    active_at TIMESTAMPTZ NOT NULL,
    expired_at TIMESTAMPTZ NOT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 13. Tabel vehicle_inspection (CSV #7 Revisi - Fix id_vehile & uui)
CREATE TABLE IF NOT EXISTS vehicle_inspection (
    vehicle_inspection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicle(vehicle_id),
    inspector_employee_id UUID NULL REFERENCES employee(employee_id),
    type inspection_type_enum NOT NULL,
    path_file VARCHAR(255) NOT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 14. Tabel work_type (CSV #1 Revisi - Terikat Divisi & Multi SOP Foto)
CREATE TABLE IF NOT EXISTS work_type (
    work_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    division_id UUID NOT NULL REFERENCES division(division_id),
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_work_type_division_name ON work_type (division_id, lower(name)) WHERE delete_at IS NULL;


-- 15. Tabel image_requirement (CSV #5 Revisi - Konfirmasi 2A & 2B: 1 work_type punya banyak syarat foto SOP)
CREATE TABLE IF NOT EXISTS image_requirement (
    image_requirement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_type_id UUID NOT NULL REFERENCES work_type(work_type_id),
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    path_image VARCHAR(255) NOT NULL, -- Contoh gambar panduan SOP (2A)
    is_mandatory BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order SMALLINT NOT NULL DEFAULT 1,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 15b. Tabel work_type_default_materials (Template Material Default BoM 1:N per Jenis Pekerjaan)
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

-- 16. Tabel work_plan_daily (Entitas Induk Rencana Kerja Harian & Jam Operasional Proyek)
CREATE TABLE IF NOT EXISTS work_plan_daily (
    daily_plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    division_id UUID NOT NULL REFERENCES division(division_id),
    team_id UUID NOT NULL REFERENCES team(team_id),
    work_date DATE NOT NULL,
    site_name VARCHAR(150) NOT NULL,
    site_lat NUMERIC(10,7) NOT NULL,
    site_lng NUMERIC(10,7) NOT NULL,
    attendance_radius_m INT NOT NULL DEFAULT 150,
    clock_in_time TIME NOT NULL DEFAULT '07:00:00',
    clock_out_time TIME NOT NULL DEFAULT '16:00:00',
    status VARCHAR(30) NOT NULL DEFAULT 'ONGOING', -- 'DRAFT','SUBMITTED','APPROVED','ONGOING','COMPLETED'
    created_by_id UUID NOT NULL REFERENCES employee(employee_id),
    approved_by_pm_id UUID NULL REFERENCES employee(employee_id),
    approved_at TIMESTAMPTZ NULL,
    rejection_reason TEXT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 17. Tabel work_plan_item (Slot Penugasan Tugas Harian, Prasyarat, & Engine Rollover)
CREATE TABLE IF NOT EXISTS work_plan_item (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_plan_id UUID NOT NULL REFERENCES work_plan_daily(daily_plan_id),
    work_type_id UUID NOT NULL REFERENCES work_type(work_type_id),
    completion_id UUID NULL, -- Di-link ke work_completion
    start_time TIME NULL DEFAULT '08:00:00',
    end_time TIME NULL DEFAULT '17:00:00',
    location_name VARCHAR(150) NULL,
    site_lat NUMERIC(10,7) NULL,
    site_lng NUMERIC(10,7) NULL,
    assigned_employee_ids JSONB NULL,
    title VARCHAR(200) NOT NULL,
    task_phase VARCHAR(30) NOT NULL DEFAULT 'MAIN_INSTALLATION', -- 'SURVEY','PREPARATION','MAIN_INSTALLATION','TESTING_COMMISSIONING'
    is_main_deliverable BOOLEAN NOT NULL DEFAULT TRUE,
    depends_on_item_id UUID NULL REFERENCES work_plan_item(item_id),
    target_qty NUMERIC(10,2) NOT NULL DEFAULT 100.00,
    completed_qty NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    progress_percent NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    status VARCHAR(30) NOT NULL DEFAULT 'IN_PROGRESS', -- 'TODO','IN_PROGRESS','DONE','PENDING_ROLLOVER','SHIFTED_DAY'
    rollover_approval_status rollover_approval_enum NOT NULL DEFAULT 'NONE',
    approved_by_pm_id UUID NULL REFERENCES employee(employee_id),
    origin_item_id UUID NULL REFERENCES work_plan_item(item_id),
    shifted_to_daily_id UUID NULL REFERENCES work_plan_daily(daily_plan_id),
    delay_reason TEXT NULL,
    realization_photos_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 18. Tabel company_mess_stay (Mencatat Lokasi Mess & Riwayat Inap Berbasis Tanggal Riil)
CREATE TABLE IF NOT EXISTS company_mess_stay (
    mess_stay_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mess_name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    latitude NUMERIC(10,7) NOT NULL,
    longitude NUMERIC(10,7) NOT NULL,
    employee_id UUID NOT NULL REFERENCES employee(employee_id),
    stay_start_date DATE NOT NULL,
    stay_end_date DATE NOT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 20. Tabel asset_assignment (Peminjaman Alat Pribadi, Alat Umum & Kendaraan - Konfirmasi 3A, 3B, 1A)
CREATE TABLE IF NOT EXISTS asset_assignment (
    assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type VARCHAR(20) NOT NULL, -- 'TOOL' atau 'VEHICLE'
    tool_id UUID NULL REFERENCES tool(tool_id),
    vehicle_id UUID NULL REFERENCES vehicle(vehicle_id),
    employee_id UUID NOT NULL REFERENCES employee(employee_id),
    daily_plan_id UUID NULL REFERENCES work_plan_daily(daily_plan_id),
    assignment_status asset_status_enum NOT NULL DEFAULT 'loaned',
    loaned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    returned_at TIMESTAMPTZ NULL, -- Jika NULL berarti belum dikembalikan (menahan proses Offboarding 1A)
    handover_photo_path VARCHAR(255) NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 21. Tabel employee_offboarding (Konfirmasi 1A: Prosedur Offboarding PKWT & Pengembalian Barang)
CREATE TABLE IF NOT EXISTS employee_offboarding (
    offboarding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employee(employee_id),
    reason_type offboarding_reason_enum NOT NULL,
    submission_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_date DATE NOT NULL,
    is_all_assets_returned BOOLEAN NOT NULL DEFAULT FALSE,
    approved_by_pm_id UUID NULL REFERENCES employee(employee_id),
    approved_by_hr_id UUID NULL REFERENCES employee(employee_id),
    status VARCHAR(30) NOT NULL DEFAULT 'CLEARANCE_PENDING', -- 'SUBMITTED','CLEARANCE_PENDING','APPROVED','COMPLETED'
    notes TEXT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 22. Tabel offboarding_clearance_item (Detail Pengembalian Barang Pinjaman saat Offboarding - 1A)
CREATE TABLE IF NOT EXISTS offboarding_clearance_item (
    clearance_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offboarding_id UUID NOT NULL REFERENCES employee_offboarding(offboarding_id),
    assignment_id UUID NOT NULL REFERENCES asset_assignment(assignment_id),
    return_condition VARCHAR(30) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'GOOD', 'DAMAGED', 'LOST'
    handover_photo_path VARCHAR(255) NULL,
    verified_by_id UUID NULL REFERENCES employee(employee_id),
    verified_at TIMESTAMPTZ NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 23. Tabel attendance (Absensi Wajah, Radius Tugas, Radius Kantor Utama & Uang Makan - Konfirmasi 5A, 5B)
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employee(employee_id),
    attendance_date DATE NOT NULL,
    target_location_type VARCHAR(25) NOT NULL, -- 'OFFICE' atau 'WORK_PLAN_DAILY'
    office_id UUID NOT NULL REFERENCES office(office_id),
    daily_plan_id UUID NULL REFERENCES work_plan_daily(daily_plan_id),
    scheduled_in TIME NOT NULL,
    scheduled_out TIME NOT NULL,
    clock_in_at TIMESTAMPTZ NOT NULL,
    clock_out_at TIMESTAMPTZ NULL,
    in_lat NUMERIC(10,7) NOT NULL,
    in_lng NUMERIC(10,7) NOT NULL,
    face_match_score NUMERIC(5,2) NOT NULL,
    face_photo_path VARCHAR(255) NOT NULL,
    distance_to_target_m INT NOT NULL,
    is_within_attendance_radius BOOLEAN NOT NULL,
    out_of_radius_photo_path VARCHAR(255) NULL,
    out_of_radius_note TEXT NULL,
    om_approval_status VARCHAR(25) NOT NULL DEFAULT 'AUTO_VALID', -- 'AUTO_VALID', 'PENDING_OM', 'APPROVED', 'REJECTED'
    distance_from_main_office_m INT NOT NULL,
    city_zone_status city_zone_enum NOT NULL,
    meal_allowance_amount NUMERIC(12,2) NOT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 23b. Tabel attendance_site_visit (Check-In multi-lokasi penugasan harian)
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
);

CREATE INDEX IF NOT EXISTS idx_site_visit_attendance ON attendance_site_visit(attendance_id);
CREATE INDEX IF NOT EXISTS idx_site_visit_item ON attendance_site_visit(item_id);

-- 24. Tabel work_completion (Parent Client Order / Proyek Klien)
CREATE TABLE IF NOT EXISTS work_completion (
    completion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    division_id UUID NULL REFERENCES division(division_id),
    pm_id UUID NULL REFERENCES employee(employee_id),
    client_name VARCHAR(150) NOT NULL DEFAULT 'Klien Umum',
    project_title VARCHAR(255) NOT NULL DEFAULT 'Pekerjaan Lapangan',
    order_number VARCHAR(50) NULL,
    total_target_unit INT NOT NULL DEFAULT 1,
    unit_measure VARCHAR(50) NOT NULL DEFAULT 'Unit',
    order_status VARCHAR(30) NOT NULL DEFAULT 'ONGOING', -- 'PENDING','CANCELLED','ONGOING','URGENT','COMPLETED'
    priority_level VARCHAR(20) NOT NULL DEFAULT 'NORMAL', -- 'LOW','NORMAL','HIGH','URGENT'
    site_address TEXT NULL,
    site_lat NUMERIC(10,7) NULL,
    site_lng NUMERIC(10,7) NULL,
    report_scope VARCHAR(15) NULL, -- 'DAILY' atau 'PROJECT'
    daily_plan_id UUID NULL REFERENCES work_plan_daily(daily_plan_id),
    start_work_date DATE NULL,
    end_work_date DATE NULL,
    summary_notes TEXT NULL,
    obstacles TEXT NULL,
    realization_photos_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    leader_signer_id UUID NULL REFERENCES employee(employee_id),
    leader_signature_path VARCHAR(255) NULL,
    leader_signed_at TIMESTAMPTZ NULL,
    pm_signer_id UUID NULL REFERENCES employee(employee_id),
    pm_signature_path VARCHAR(255) NULL,
    pm_signed_at TIMESTAMPTZ NULL,
    signature_hash CHAR(64) NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 24b. Tabel work_completion_bom (Bon Material Riil Proyek / Order Klien)
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

-- 24c. Tabel document_template_export (Ekspor Berkas Multi-Format & Preview)
CREATE TABLE IF NOT EXISTS document_template_export (
    export_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(30) NOT NULL DEFAULT 'WORK_COMPLETION', -- 'WORK_COMPLETION', 'WORK_PLAN_PERIODIC', 'WORK_PLAN_DAILY'
    completion_id UUID NULL REFERENCES work_completion(completion_id),
    daily_plan_id UUID NULL REFERENCES work_plan_daily(daily_plan_id),
    period_start_date DATE NULL,
    period_end_date DATE NULL,
    template_type VARCHAR(40) NOT NULL, -- 'DAILY_TEMPLATE', 'PERIODIC_TEMPLATE'
    master_template_path VARCHAR(255) NOT NULL, -- File template baku perusahaan (6C)
    export_format export_format_enum NOT NULL,
    file_output_url VARCHAR(255) NOT NULL,
    generated_by_id UUID NOT NULL REFERENCES employee(employee_id),
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

-- 25. Tabel app_activity_logs (Partisi Bulanan Ringan Berbasis JSONB changed_diff)
CREATE TABLE IF NOT EXISTS app_activity_logs (
    log_id UUID NOT NULL DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_user_id UUID NULL,
    actor_role VARCHAR(30) NOT NULL,
    platform client_platform_enum NOT NULL,
    action VARCHAR(40) NOT NULL,
    entity_table VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    changed_diff JSONB NOT NULL,
    ip_address INET NULL,
    gps_location VARCHAR(50) NULL,
    PRIMARY KEY (log_id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE IF NOT EXISTS app_activity_logs_2026_10 PARTITION OF app_activity_logs
    FOR VALUES FROM ('2026-10-01 00:00:00+07') TO ('2026-11-01 00:00:00+07');

CREATE TABLE IF NOT EXISTS app_activity_logs_2026_11 PARTITION OF app_activity_logs
    FOR VALUES FROM ('2026-11-01 00:00:00+07') TO ('2026-12-01 00:00:00+07');

CREATE INDEX IF NOT EXISTS idx_activity_logs_entity ON app_activity_logs (entity_table, entity_id);

-- 26. Tabel system_backup_registry (Pencatatan Backup 1 Bulan & 6 Bulan)
CREATE TABLE IF NOT EXISTS system_backup_registry (
    backup_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_cycle VARCHAR(30) NOT NULL, -- 'MONTHLY_SNAPSHOT', 'SIX_MONTH_ARCHIVE'
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    file_path_url VARCHAR(255) NOT NULL,
    compressed_size_mb NUMERIC(10,2) NOT NULL,
    sha256_checksum CHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'VERIFIED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 27. Tabel overtime (Pengajuan & Persetujuan Lembur per Rencana Kerja)
CREATE TABLE IF NOT EXISTS overtime (
    overtime_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_plan_id UUID NULL REFERENCES work_plan_daily(daily_plan_id),
    employee_id UUID NOT NULL REFERENCES employee(employee_id),
    work_date DATE NOT NULL,
    hours NUMERIC(4,2) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING_PM',
    reviewed_by_id UUID NULL REFERENCES employee(employee_id),
    reviewed_at TIMESTAMPTZ NULL,
    review_note TEXT NULL,
    create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_overtime_daily_plan ON overtime (daily_plan_id);
CREATE INDEX IF NOT EXISTS idx_overtime_employee ON overtime (employee_id);

-- Indeks Tambahan untuk Relasi Foreign Key & Filter Soft Delete
CREATE INDEX IF NOT EXISTS idx_employee_office ON employee (office_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_employee_division ON employee (division_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions (user_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_division_om ON division (om_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_division_pm ON division (pm_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_team_office ON team (office_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_team_division ON team (division_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_team_leader ON team (leader_employee_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_member_team ON member (team_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_member_employee ON member (employee_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_address_employee ON address (employee_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_employee_file_employee ON employee_file (employee_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tool_office ON tool (office_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tool_division ON tool (division_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_vehicle_office ON vehicle (office_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_vehicle_division ON vehicle (division_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_vehicle_file_vehicle ON vehicle_file (vehicle_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_vehicle_inspection_vehicle ON vehicle_inspection (vehicle_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_plan_daily_division ON work_plan_daily (division_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_plan_daily_team ON work_plan_daily (team_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_plan_daily_date ON work_plan_daily (work_date) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_plan_item_daily ON work_plan_item (daily_plan_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_plan_item_phase ON work_plan_item (task_phase) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_plan_item_deliverable ON work_plan_item (is_main_deliverable) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_plan_item_work_type ON work_plan_item (work_type_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_type_division ON work_type (division_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_asset_assignment_tool ON asset_assignment (tool_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_asset_assignment_vehicle ON asset_assignment (vehicle_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_asset_assignment_employee ON asset_assignment (employee_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_attendance_employee ON attendance (employee_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_attendance_office ON attendance (office_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_attendance_daily_plan ON attendance (daily_plan_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_work_completion_daily ON work_completion (daily_plan_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_wt_default_materials_type ON work_type_default_materials (work_type_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_wc_bom_completion ON work_completion_bom (completion_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_wc_bom_item ON work_completion_bom (work_plan_item_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_offboarding_employee ON employee_offboarding (employee_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_clearance_offboarding ON offboarding_clearance_item (offboarding_id) WHERE delete_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_clearance_assignment ON offboarding_clearance_item (assignment_id) WHERE delete_at IS NULL;

COMMIT;
