-- =====================================================================
-- 08 · Master Schema V2 — tambahan Milestone 10 (master data) yang belum tercatat di 06
-- Klien, proyek, jabatan, cuti, biaya operasional + kolom relasinya. IDEMPOTEN: aman dijalankan ulang.
-- Urutan pasang V2: 06_master_schema_v2.sql -> 08_master_v2_tambahan.sql -> (aplikasi) migration_v3.
-- =====================================================================

DO $$ BEGIN CREATE TYPE approval_status_enum AS ENUM ('PENDING', 'APPROVED_BY_PM', 'APPROVED_BY_HR',
  'APPROVED_BY_FINANCE', 'REJECTED', 'CANCELLED'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE expense_category_enum AS ENUM ('FUEL', 'TOLL_PARKING', 'EMERGENCY_MATERIAL',
  'ACCOMMODATION', 'OTHER'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE leave_type_enum AS ENUM ('ANNUAL', 'SICK', 'MATERNITY', 'UNPAID', 'OTHER');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS public.client (
    client_id uuid DEFAULT gen_random_uuid() NOT NULL,
    client_code character varying(30) NOT NULL,
    name character varying(150) NOT NULL,
    pic_name character varying(100),
    pic_phone character varying(30),
    address text,
    status boolean DEFAULT true NOT NULL,
    create_at timestamp with time zone DEFAULT now() NOT NULL,
    update_at timestamp with time zone DEFAULT now() NOT NULL,
    delete_at timestamp with time zone
);
CREATE TABLE IF NOT EXISTS public.job_position (
    position_id uuid DEFAULT gen_random_uuid() NOT NULL,
    division_id uuid,
    code character varying(30) NOT NULL,
    name character varying(100) NOT NULL,
    grade_level smallint DEFAULT 1 NOT NULL,
    daily_allowance numeric(12,2) DEFAULT 0.00 NOT NULL,
    description text,
    status boolean DEFAULT true NOT NULL,
    create_at timestamp with time zone DEFAULT now() NOT NULL,
    update_at timestamp with time zone DEFAULT now() NOT NULL,
    delete_at timestamp with time zone
);
CREATE TABLE IF NOT EXISTS public.leave_balance (
    balance_id uuid DEFAULT gen_random_uuid() NOT NULL,
    employee_id uuid NOT NULL,
    period_year smallint NOT NULL,
    total_quota smallint DEFAULT 12 NOT NULL,
    used_quota smallint DEFAULT 0 NOT NULL,
    create_at timestamp with time zone DEFAULT now() NOT NULL,
    update_at timestamp with time zone DEFAULT now() NOT NULL,
    delete_at timestamp with time zone
);
CREATE TABLE IF NOT EXISTS public.leave_request (
    leave_id uuid DEFAULT gen_random_uuid() NOT NULL,
    employee_id uuid NOT NULL,
    leave_type public.leave_type_enum NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    total_days smallint DEFAULT 1 NOT NULL,
    reason text NOT NULL,
    attachment_path character varying(255),
    status public.approval_status_enum DEFAULT 'PENDING'::public.approval_status_enum NOT NULL,
    reviewed_by_pm_id uuid,
    reviewed_by_hr_id uuid,
    reviewed_at timestamp with time zone,
    rejection_note text,
    cancel_note text,
    create_at timestamp with time zone DEFAULT now() NOT NULL,
    update_at timestamp with time zone DEFAULT now() NOT NULL,
    delete_at timestamp with time zone,
    CONSTRAINT ck_leave_dates CHECK ((end_date >= start_date))
);
CREATE TABLE IF NOT EXISTS public.operational_expense (
    expense_id uuid DEFAULT gen_random_uuid() NOT NULL,
    office_id uuid NOT NULL,
    daily_plan_id uuid,
    vehicle_id uuid,
    requester_id uuid NOT NULL,
    expense_date date DEFAULT CURRENT_DATE NOT NULL,
    category public.expense_category_enum NOT NULL,
    amount numeric(12,2) NOT NULL,
    description text NOT NULL,
    receipt_photo_path character varying(255) NOT NULL,
    odometer_km integer,
    status public.approval_status_enum DEFAULT 'PENDING'::public.approval_status_enum NOT NULL,
    approved_by_id uuid,
    approved_at timestamp with time zone,
    rejection_note text,
    create_at timestamp with time zone DEFAULT now() NOT NULL,
    update_at timestamp with time zone DEFAULT now() NOT NULL,
    delete_at timestamp with time zone
);
CREATE TABLE IF NOT EXISTS public.project (
    project_id uuid DEFAULT gen_random_uuid() NOT NULL,
    client_id uuid NOT NULL,
    office_id uuid NOT NULL,
    division_id uuid NOT NULL,
    pm_id uuid NOT NULL,
    spk_number character varying(100) NOT NULL,
    project_title character varying(255) NOT NULL,
    total_target_qty numeric(12,2) DEFAULT 1.00 NOT NULL,
    unit_measure character varying(50) DEFAULT 'Unit'::character varying NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    status character varying(30) DEFAULT 'ONGOING'::character varying NOT NULL,
    create_at timestamp with time zone DEFAULT now() NOT NULL,
    update_at timestamp with time zone DEFAULT now() NOT NULL,
    delete_at timestamp with time zone,
    CONSTRAINT ck_project_status CHECK (((status)::text = ANY (ARRAY['DRAFT'::text, 'ONGOING'::text, 'COMPLETED'::text, 'CANCELLED'::text])))
);
DO $$ BEGIN
    ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_pkey PRIMARY KEY (client_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.job_position
    ADD CONSTRAINT job_position_pkey PRIMARY KEY (position_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.leave_balance
    ADD CONSTRAINT leave_balance_pkey PRIMARY KEY (balance_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.leave_request
    ADD CONSTRAINT leave_request_pkey PRIMARY KEY (leave_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.operational_expense
    ADD CONSTRAINT operational_expense_pkey PRIMARY KEY (expense_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_pkey PRIMARY KEY (project_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
CREATE INDEX IF NOT EXISTS idx_expense_daily_plan ON public.operational_expense USING btree (daily_plan_id) WHERE (delete_at IS NULL);
CREATE INDEX IF NOT EXISTS idx_expense_requester ON public.operational_expense USING btree (requester_id) WHERE (delete_at IS NULL);
CREATE INDEX IF NOT EXISTS idx_job_position_division ON public.job_position USING btree (division_id) WHERE (delete_at IS NULL);
CREATE INDEX IF NOT EXISTS idx_leave_request_dates ON public.leave_request USING btree (start_date, end_date) WHERE (delete_at IS NULL);
CREATE INDEX IF NOT EXISTS idx_leave_request_employee ON public.leave_request USING btree (employee_id) WHERE (delete_at IS NULL);
CREATE INDEX IF NOT EXISTS idx_project_division ON public.project USING btree (division_id) WHERE (delete_at IS NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uq_client_code_active ON public.client USING btree (lower((client_code)::text)) WHERE (delete_at IS NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uq_job_position_code_active ON public.job_position USING btree (lower((code)::text)) WHERE (delete_at IS NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uq_leave_balance_emp_year ON public.leave_balance USING btree (employee_id, period_year) WHERE (delete_at IS NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uq_project_spk_active ON public.project USING btree (lower((spk_number)::text)) WHERE (delete_at IS NULL);
DO $$ BEGIN
    ALTER TABLE ONLY public.operational_expense
    ADD CONSTRAINT fk_expense_approver FOREIGN KEY (approved_by_id) REFERENCES public.employee(employee_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.operational_expense
    ADD CONSTRAINT fk_expense_daily_plan FOREIGN KEY (daily_plan_id) REFERENCES public.work_plan_daily(daily_plan_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.operational_expense
    ADD CONSTRAINT fk_expense_office FOREIGN KEY (office_id) REFERENCES public.office(office_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.operational_expense
    ADD CONSTRAINT fk_expense_requester FOREIGN KEY (requester_id) REFERENCES public.employee(employee_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.operational_expense
    ADD CONSTRAINT fk_expense_vehicle FOREIGN KEY (vehicle_id) REFERENCES public.vehicle(vehicle_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.job_position
    ADD CONSTRAINT fk_job_position_division FOREIGN KEY (division_id) REFERENCES public.division(division_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.leave_balance
    ADD CONSTRAINT fk_leave_balance_employee FOREIGN KEY (employee_id) REFERENCES public.employee(employee_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.leave_request
    ADD CONSTRAINT fk_leave_request_employee FOREIGN KEY (employee_id) REFERENCES public.employee(employee_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.leave_request
    ADD CONSTRAINT fk_leave_request_hr FOREIGN KEY (reviewed_by_hr_id) REFERENCES public.employee(employee_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.leave_request
    ADD CONSTRAINT fk_leave_request_pm FOREIGN KEY (reviewed_by_pm_id) REFERENCES public.employee(employee_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk_project_client FOREIGN KEY (client_id) REFERENCES public.client(client_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk_project_division FOREIGN KEY (division_id) REFERENCES public.division(division_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk_project_office FOREIGN KEY (office_id) REFERENCES public.office(office_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk_project_pm FOREIGN KEY (pm_id) REFERENCES public.employee(employee_id);
EXCEPTION WHEN duplicate_object OR invalid_table_definition THEN NULL; END $$;

-- Kolom relasi ke tabel di atas
ALTER TABLE employee ADD COLUMN IF NOT EXISTS position_id uuid;
ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS project_id uuid;
ALTER TABLE work_plan_daily ADD COLUMN IF NOT EXISTS project_id uuid;
DO $$ BEGIN
    ALTER TABLE employee ADD CONSTRAINT fk_employee_position FOREIGN KEY (position_id) REFERENCES job_position(position_id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE work_completion ADD CONSTRAINT fk_work_completion_project FOREIGN KEY (project_id) REFERENCES project(project_id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE work_plan_daily ADD CONSTRAINT fk_work_plan_daily_project FOREIGN KEY (project_id) REFERENCES project(project_id);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
