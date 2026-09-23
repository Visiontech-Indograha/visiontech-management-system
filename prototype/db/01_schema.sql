-- =============================================================================
-- Visiontech VMS · Skema basis data PostgreSQL 16+ (PostGIS 3.4+, pgvector 0.7+)
-- Berkas 1 dari 5: ekstensi, tipe, tabel, indeks, dan batasan.
-- Urutan pemasangan: 01_schema → 02_functions → 03_policies → 04_signature_auth → 05_face
--
-- Prinsip:
--   1. Multi-tenant sejak awal (organization_id ada di setiap tabel bisnis).
--   2. Dokumen terbit tidak pernah berubah: snapshot JSONB + hash, dikunci trigger.
--   3. Semua perubahan tercatat di audit_event.
--   4. Identitas baris memakai UUID v7 (urut waktu) agar indeks tetap padat.
--   5. Siap tumbuh: tabel deret waktu dipartisi bulanan sejak hari pertama.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;      -- geofence absensi & lokasi proyek
CREATE EXTENSION IF NOT EXISTS vector;       -- pengenalan wajah (embedding 512 dimensi)
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- hash token QR, digest snapshot
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- exclusion constraint jadwal personel
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- pencarian nama/kode yang toleran typo
CREATE EXTENSION IF NOT EXISTS citext;       -- email & login tanpa peduli huruf besar/kecil

CREATE SCHEMA IF NOT EXISTS vms;
SET search_path = vms, public;

-- Kunci utama memakai UUID acak. Pada PostgreSQL 18+ ganti isi fungsi ini dengan
-- uuidv7() bawaan agar nilainya urut waktu dan indeks tetap padat.
CREATE OR REPLACE FUNCTION new_id() RETURNS uuid
LANGUAGE sql VOLATILE AS $$ SELECT gen_random_uuid() $$;

-- -----------------------------------------------------------------------------
-- Tipe enum: status yang dipakai aplikasi. Enum dipilih (bukan lookup table)
-- karena nilainya melekat pada aturan bisnis dan divalidasi di banyak tempat.
-- Menambah nilai baru cukup ALTER TYPE ... ADD VALUE (tanpa penulisan ulang tabel).
-- -----------------------------------------------------------------------------
CREATE TYPE role_code AS ENUM ('PM','LEADER','MEMBER','FINANCE','HR','ASSET','OPS','ADMIN');
CREATE TYPE plan_status AS ENUM ('DRAFT','PUBLISHED','ACCEPTED','APPEALED','IN_PROGRESS','COMPLETION_REVIEW','COMPLETED','CANCELLED');
CREATE TYPE document_kind AS ENUM ('INITIAL_ORDER','REVISION','ADDENDUM','PERSONNEL_ADDENDUM');
CREATE TYPE document_status AS ENUM ('AWAITING_ACCEPTANCE','EFFECTIVE','SUPERSEDED','REJECTED','WITHDRAWN');
CREATE TYPE change_type AS ENUM ('EXTEND','PERSONNEL');
CREATE TYPE change_status AS ENUM ('PENDING_PM','AWAITING_LEADER_ACCEPTANCE','EFFECTIVE','REJECTED','WITHDRAWN');
CREATE TYPE report_status AS ENUM ('DRAFT','SUBMITTED','CHANGES_REQUESTED','APPROVED');
CREATE TYPE attendance_source AS ENUM ('MOBILE','MACHINE');
CREATE TYPE attendance_status AS ENUM ('AUTO_VALID','NEEDS_REVIEW','APPROVED','REJECTED');
CREATE TYPE asset_kind AS ENUM ('VEHICLE','TOOL');
CREATE TYPE asset_status AS ENUM ('AVAILABLE','RESERVED','IN_USE','RETURN_PENDING','MAINTENANCE','RETIRED');
CREATE TYPE personal_document_status AS ENUM ('PENDING','VERIFIED','REJECTED');
CREATE TYPE personal_document_lifecycle AS ENUM ('PENDING','CURRENT','SUPERSEDED','EXPIRED');
CREATE TYPE incident_category AS ENUM ('K3_RINGAN','K3_BERAT','K3_LINGKUNGAN','K3_HAMPIR','ASET');
CREATE TYPE incident_severity AS ENUM ('RENDAH','SEDANG','TINGGI','KRITIS');
CREATE TYPE incident_status AS ENUM ('OPEN','IN_REVIEW','RESOLVED');
CREATE TYPE approval_status AS ENUM ('PENDING_PM','APPROVED','REJECTED');
CREATE TYPE qr_purpose AS ENUM ('DOCUMENT_VERIFY','ASSET_HANDOVER','ATTENDANCE_SITE','VISITOR_PASS');
CREATE TYPE qr_scan_result AS ENUM ('VALID','EXPIRED','REVOKED','OUT_OF_RANGE','LIMIT_REACHED','UNKNOWN_TOKEN','WRONG_PURPOSE');
CREATE TYPE sync_status AS ENUM ('PENDING','APPLIED','CONFLICT','REJECTED');

-- -----------------------------------------------------------------------------
-- Tenant & organisasi
-- -----------------------------------------------------------------------------
CREATE TABLE organization (
  id            uuid PRIMARY KEY DEFAULT new_id(),
  name          text NOT NULL,
  timezone      text NOT NULL DEFAULT 'Asia/Jakarta',
  shift_start   time NOT NULL DEFAULT '08:00',
  shift_end     time NOT NULL DEFAULT '17:00',
  geofence_radius_m integer NOT NULL DEFAULT 100 CHECK (geofence_radius_m BETWEEN 10 AND 5000),
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
COMMENT ON COLUMN organization.geofence_radius_m IS 'Radius default; dapat ditimpa per lokasi proyek.';

CREATE TABLE business_unit (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  code            text NOT NULL,
  name            text NOT NULL,
  deleted_at      timestamptz,
  UNIQUE (organization_id, code)
);

-- -----------------------------------------------------------------------------
-- Orang, akun, dan peran
--   employee  = data kepegawaian (sumber kebenaran SDM)
--   app_user  = kredensial login; satu karyawan boleh tanpa akun
--   user_role = peran global (PM/HR/…) yang dibatasi unit
-- Kewenangan pada satu pekerjaan tetap mengikuti penugasan di SK
-- (lihat work_plan_member), bukan hanya peran global.
-- -----------------------------------------------------------------------------
CREATE TABLE employee (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  employee_no     text NOT NULL,
  full_name       text NOT NULL,
  position        text NOT NULL,
  unit_id         uuid REFERENCES business_unit(id),
  email           citext,
  phone           text,
  join_date       date NOT NULL,
  birth_date      date,
  address         text,
  emergency_contact text,
  is_active       boolean NOT NULL DEFAULT true,
  offboarded_at   timestamptz,
  offboarding_reason text,
  deleted_at      timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, employee_no)
);
CREATE INDEX employee_unit_idx ON employee (organization_id, unit_id) WHERE deleted_at IS NULL;
CREATE INDEX employee_name_trgm_idx ON employee USING gin (full_name gin_trgm_ops);

CREATE TABLE employee_assignment (          -- riwayat penempatan/jabatan
  id           uuid PRIMARY KEY DEFAULT new_id(),
  employee_id  uuid NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
  position     text NOT NULL,
  unit_id      uuid REFERENCES business_unit(id),
  valid_from   date NOT NULL,
  valid_to     date,
  CHECK (valid_to IS NULL OR valid_to >= valid_from)
);
CREATE INDEX employee_assignment_emp_idx ON employee_assignment (employee_id, valid_from DESC);

CREATE TABLE app_user (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  employee_id     uuid UNIQUE REFERENCES employee(id) ON DELETE RESTRICT,
  login           citext NOT NULL,
  password_hash   text,                     -- argon2id; NULL bila memakai SSO
  mfa_secret_enc  bytea,                    -- dienkripsi di aplikasi, bukan plaintext
  is_active       boolean NOT NULL DEFAULT true,
  last_login_at   timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, login)
);

CREATE TABLE user_role (
  id        uuid PRIMARY KEY DEFAULT new_id(),
  user_id   uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  role      role_code NOT NULL,
  unit_id   uuid REFERENCES business_unit(id)    -- NULL = lintas unit (OPS/HR/FINANCE)
);
-- NULL tidak dianggap sama dengan NULL oleh UNIQUE biasa, jadi dipakai indeks ekspresi.
CREATE UNIQUE INDEX user_role_uidx ON user_role
  (user_id, role, COALESCE(unit_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- -----------------------------------------------------------------------------
-- Berkas: metadata saja. Isi berkas disimpan di object storage (S3/MinIO).
-- Basis data tidak pernah menyimpan isi berkas, hanya kunci penyimpanannya.
-- -----------------------------------------------------------------------------
CREATE TABLE file_object (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  storage_key     text NOT NULL UNIQUE,      -- kunci privat; URL publik tidak disimpan
  file_name       text NOT NULL,
  mime_type       text NOT NULL,
  byte_size       bigint NOT NULL CHECK (byte_size > 0 AND byte_size <= 10485760),
  sha256          bytea NOT NULL,            -- deduplikasi & bukti keutuhan
  uploaded_by     uuid REFERENCES app_user(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, sha256)
);
-- -----------------------------------------------------------------------------
-- Lokasi proyek: titik geografis + radius toleransi absensi
-- -----------------------------------------------------------------------------
CREATE TABLE site (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  name            text NOT NULL,
  address         text,
  location        geography(Point,4326) NOT NULL,
  radius_m        integer CHECK (radius_m BETWEEN 10 AND 5000),  -- NULL = pakai default organisasi
  deleted_at      timestamptz,
  UNIQUE (organization_id, name)
);
CREATE INDEX site_location_gix ON site USING gist (location);

-- -----------------------------------------------------------------------------
-- Work plan (SK) dan susunannya
-- -----------------------------------------------------------------------------
CREATE TABLE work_plan (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  unit_id         uuid NOT NULL REFERENCES business_unit(id),
  site_id         uuid REFERENCES site(id),
  number          text,                        -- nomor SK; NULL selama masih draft
  title           text NOT NULL,
  location_text   text NOT NULL,               -- teks lokasi apa adanya dari lapangan
  description     text,
  period          daterange NOT NULL,          -- [mulai, selesai]; eksklusif di ujung atas
  status          plan_status NOT NULL DEFAULT 'DRAFT',
  pm_employee_id      uuid NOT NULL REFERENCES employee(id),
  leader_employee_id  uuid REFERENCES employee(id),
  revision        integer NOT NULL DEFAULT 1,
  row_version     integer NOT NULL DEFAULT 1,  -- penguncian optimistis antar-tab
  cancellation_reason text,
  deleted_at      timestamptz,                 -- arsip draft (soft delete)
  created_by      uuid REFERENCES app_user(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, number),
  CHECK (NOT isempty(period)),
  CHECK (leader_employee_id IS NULL OR leader_employee_id <> pm_employee_id)
);
CREATE INDEX work_plan_unit_status_idx ON work_plan (organization_id, unit_id, status) WHERE deleted_at IS NULL;
CREATE INDEX work_plan_period_gix ON work_plan USING gist (period);

CREATE TABLE work_plan_member (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  work_plan_id    uuid NOT NULL REFERENCES work_plan(id) ON DELETE CASCADE,
  employee_id     uuid NOT NULL REFERENCES employee(id),
  role_in_plan    role_code NOT NULL CHECK (role_in_plan IN ('LEADER','MEMBER')),
  valid_period    daterange NOT NULL,          -- adendum personel menutup baris lama
  added_by_document_id uuid,                   -- FK ditambahkan setelah plan_document dibuat
  removed_reason  text
);
CREATE INDEX work_plan_member_plan_idx ON work_plan_member (work_plan_id);
CREATE INDEX work_plan_member_employee_gix ON work_plan_member USING gist (employee_id, valid_period);

CREATE TABLE work_plan_day (
  id            uuid PRIMARY KEY DEFAULT new_id(),
  work_plan_id  uuid NOT NULL REFERENCES work_plan(id) ON DELETE CASCADE,
  work_date     date NOT NULL,
  title         text NOT NULL,
  sort_order    integer NOT NULL DEFAULT 0,
  UNIQUE (work_plan_id, work_date)
);

CREATE TABLE work_plan_task (
  id                uuid PRIMARY KEY DEFAULT new_id(),
  work_plan_day_id  uuid NOT NULL REFERENCES work_plan_day(id) ON DELETE CASCADE,
  title             text NOT NULL,
  is_done           boolean NOT NULL DEFAULT false,
  done_at           timestamptz,
  done_by           uuid REFERENCES employee(id),
  sort_order        integer NOT NULL DEFAULT 0
);
CREATE INDEX work_plan_task_day_idx ON work_plan_task (work_plan_day_id);

-- -----------------------------------------------------------------------------
-- Laporan harian, mingguan, dan laporan akhir
-- -----------------------------------------------------------------------------
CREATE TABLE daily_report (
  id                uuid PRIMARY KEY DEFAULT new_id(),
  work_plan_day_id  uuid NOT NULL UNIQUE REFERENCES work_plan_day(id) ON DELETE CASCADE,
  status            report_status NOT NULL DEFAULT 'DRAFT',
  body              text NOT NULL DEFAULT '',
  obstacle          text NOT NULL DEFAULT '',
  submitted_by      uuid REFERENCES employee(id),
  submitted_at      timestamptz,
  reviewed_by       uuid REFERENCES employee(id),
  reviewed_at       timestamptz,
  review_note       text,
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CHECK (status <> 'SUBMITTED' OR (submitted_by IS NOT NULL AND length(btrim(body)) >= 10))
);

CREATE TABLE report_evidence (
  daily_report_id uuid NOT NULL REFERENCES daily_report(id) ON DELETE CASCADE,
  file_id         uuid NOT NULL REFERENCES file_object(id),
  PRIMARY KEY (daily_report_id, file_id)
);

CREATE TABLE weekly_report (
  id            uuid PRIMARY KEY DEFAULT new_id(),
  work_plan_id  uuid NOT NULL REFERENCES work_plan(id) ON DELETE CASCADE,
  name          text NOT NULL,
  covered_period daterange NOT NULL,
  status        report_status NOT NULL DEFAULT 'DRAFT',
  body          text NOT NULL DEFAULT '',
  obstacle      text NOT NULL DEFAULT '',
  submitted_by  uuid REFERENCES employee(id),
  reviewed_by   uuid REFERENCES employee(id),
  review_note   text,
  UNIQUE (work_plan_id, name)
);

CREATE TABLE final_report (
  work_plan_id  uuid PRIMARY KEY REFERENCES work_plan(id) ON DELETE CASCADE,
  status        report_status NOT NULL DEFAULT 'DRAFT',
  body          text NOT NULL DEFAULT '',
  obstacle      text NOT NULL DEFAULT '',
  submitted_by  uuid REFERENCES employee(id),
  submitted_at  timestamptz,
  reviewed_by   uuid REFERENCES employee(id),
  reviewed_at   timestamptz,
  review_note   text
);

CREATE TABLE final_report_evidence (
  work_plan_id uuid NOT NULL REFERENCES final_report(work_plan_id) ON DELETE CASCADE,
  file_id      uuid NOT NULL REFERENCES file_object(id),
  PRIMARY KEY (work_plan_id, file_id)
);

-- -----------------------------------------------------------------------------
-- Dokumen SK berversi. Baris ini IMMUTABLE setelah dibuat (lihat trigger).
-- snapshot = keadaan pekerjaan saat diterbitkan, sehingga dokumen lama tidak
-- pernah ikut berubah ketika data karyawan atau jadwal berubah.
-- -----------------------------------------------------------------------------
CREATE TABLE plan_document (
  id            uuid PRIMARY KEY DEFAULT new_id(),
  work_plan_id  uuid NOT NULL REFERENCES work_plan(id) ON DELETE CASCADE,
  kind          document_kind NOT NULL,
  version       integer NOT NULL CHECK (version >= 1),
  number        text NOT NULL,
  status        document_status NOT NULL DEFAULT 'AWAITING_ACCEPTANCE',
  snapshot      jsonb NOT NULL,
  snapshot_sha256 bytea NOT NULL,             -- bukti keutuhan isi dokumen
  reason        text,
  issued_by     uuid NOT NULL REFERENCES employee(id),
  issued_at     timestamptz NOT NULL DEFAULT now(),
  accepted_by   uuid REFERENCES employee(id),
  accepted_at   timestamptz,
  UNIQUE (work_plan_id, version)
);
CREATE INDEX plan_document_plan_idx ON plan_document (work_plan_id, version DESC);
CREATE INDEX plan_document_snapshot_gin ON plan_document USING gin (snapshot jsonb_path_ops);

ALTER TABLE work_plan_member
  ADD CONSTRAINT work_plan_member_document_fk
  FOREIGN KEY (added_by_document_id) REFERENCES plan_document(id);

CREATE TABLE plan_change (                    -- usulan perpanjangan / adendum personel
  id                uuid PRIMARY KEY DEFAULT new_id(),
  work_plan_id      uuid NOT NULL REFERENCES work_plan(id) ON DELETE CASCADE,
  change_type       change_type NOT NULL,
  status            change_status NOT NULL DEFAULT 'PENDING_PM',
  reason            text NOT NULL,
  old_period        daterange,
  new_period        daterange,
  proposed_leader_id uuid REFERENCES employee(id),
  proposed_members  uuid[] NOT NULL DEFAULT '{}',
  base_revision     integer NOT NULL,
  proposed_revision integer NOT NULL,
  document_id       uuid REFERENCES plan_document(id),
  requested_by      uuid NOT NULL REFERENCES employee(id),
  decided_by        uuid REFERENCES employee(id),
  decision_reason   text,
  created_at        timestamptz NOT NULL DEFAULT now()
);
-- Hanya satu usulan terbuka per pekerjaan.
CREATE UNIQUE INDEX plan_change_open_uidx ON plan_change (work_plan_id)
  WHERE status IN ('PENDING_PM','AWAITING_LEADER_ACCEPTANCE');

-- -----------------------------------------------------------------------------
-- Aset & kendaraan
-- -----------------------------------------------------------------------------
CREATE TABLE asset (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  kind            asset_kind NOT NULL,
  vehicle_type    text CHECK (kind = 'VEHICLE' OR vehicle_type IS NULL),
  code            text NOT NULL,
  name            text NOT NULL,
  condition       text NOT NULL DEFAULT 'Baik',
  status          asset_status NOT NULL DEFAULT 'AVAILABLE',
  deleted_at      timestamptz,
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, code)
);

CREATE TABLE asset_allocation (
  id            uuid PRIMARY KEY DEFAULT new_id(),
  asset_id      uuid NOT NULL REFERENCES asset(id) ON DELETE CASCADE,
  work_plan_id  uuid NOT NULL REFERENCES work_plan(id) ON DELETE CASCADE,
  driver_employee_id uuid REFERENCES employee(id),   -- wajib untuk kendaraan
  driver_checked_at  timestamptz,                     -- pemeriksaan kelayakan oleh pengemudi
  allocated_by  uuid NOT NULL REFERENCES employee(id),
  allocated_at  timestamptz NOT NULL DEFAULT now(),
  released_at   timestamptz,
  active_range  tstzrange GENERATED ALWAYS AS (tstzrange(allocated_at, released_at)) STORED
);
-- Satu aset tidak boleh dialokasikan ke dua pekerjaan pada waktu bersamaan.
ALTER TABLE asset_allocation
  ADD CONSTRAINT asset_allocation_no_overlap
  EXCLUDE USING gist (asset_id WITH =, active_range WITH &&);

CREATE TABLE asset_return (
  id                uuid PRIMARY KEY DEFAULT new_id(),
  asset_allocation_id uuid NOT NULL REFERENCES asset_allocation(id) ON DELETE CASCADE,
  requested_by      uuid NOT NULL REFERENCES employee(id),
  requested_at      timestamptz NOT NULL DEFAULT now(),
  verified_by       uuid REFERENCES employee(id),
  verified_at       timestamptz,
  condition_on_return text,
  note              text,
  is_accepted       boolean,
  -- pengaju tidak boleh menjadi pemeriksa
  CHECK (verified_by IS NULL OR verified_by <> requested_by)
);

-- -----------------------------------------------------------------------------
-- Dokumen pribadi karyawan (SIM, sertifikat K3, kontrak)
-- -----------------------------------------------------------------------------
CREATE TABLE employee_document (
  id            uuid PRIMARY KEY DEFAULT new_id(),
  employee_id   uuid NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
  doc_type      text NOT NULL,
  number_masked text NOT NULL,               -- nomor penuh tidak pernah disimpan
  number_sha256 bytea,                       -- untuk deteksi duplikat tanpa membuka data
  expiry_date   date,
  status        personal_document_status NOT NULL DEFAULT 'PENDING',
  lifecycle     personal_document_lifecycle NOT NULL DEFAULT 'PENDING',
  file_id       uuid REFERENCES file_object(id),
  uploaded_by   uuid NOT NULL REFERENCES app_user(id),
  verified_by   uuid REFERENCES app_user(id),
  verified_at   timestamptz,
  review_note   text,
  supersedes_id uuid REFERENCES employee_document(id),
  created_at    timestamptz NOT NULL DEFAULT now(),
  -- pemilik atau pengunggah tidak boleh memverifikasi dokumennya sendiri
  CHECK (verified_by IS NULL OR verified_by <> uploaded_by)
);
-- Satu jenis dokumen hanya boleh punya satu pengajuan tertunda dan satu versi berlaku.
CREATE UNIQUE INDEX employee_document_pending_uidx ON employee_document (employee_id, doc_type) WHERE status = 'PENDING';
CREATE UNIQUE INDEX employee_document_current_uidx ON employee_document (employee_id, doc_type) WHERE lifecycle = 'CURRENT';
CREATE INDEX employee_document_expiry_idx ON employee_document (expiry_date) WHERE lifecycle = 'CURRENT';

-- -----------------------------------------------------------------------------
-- Absensi: tanggal + jam nyata, titik GPS, jarak, dan swafoto bila di luar radius
-- Dipartisi bulanan karena inilah tabel yang tumbuh paling cepat.
-- -----------------------------------------------------------------------------
CREATE TABLE attendance (
  id              uuid NOT NULL DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  employee_id     uuid NOT NULL REFERENCES employee(id),
  work_date       date NOT NULL,
  site_id         uuid REFERENCES site(id),
  site_label      text NOT NULL,
  source          attendance_source NOT NULL DEFAULT 'MOBILE',
  check_in_at     timestamptz NOT NULL,
  check_out_at    timestamptz,
  location        geography(Point,4326),      -- NULL untuk sumber mesin
  location_origin text CHECK (location_origin IN ('GPS','SIMULASI','MESIN')),
  distance_m      numeric(8,1) NOT NULL DEFAULT 0 CHECK (distance_m >= 0),
  radius_m        integer NOT NULL,
  is_late         boolean NOT NULL DEFAULT false,
  is_early_leave  boolean NOT NULL DEFAULT false,
  selfie_file_id  uuid REFERENCES file_object(id),
  status          attendance_status NOT NULL DEFAULT 'AUTO_VALID',
  explanation     text,
  reviewed_by     uuid REFERENCES employee(id),
  reviewed_at     timestamptz,
  review_note     text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id, work_date),
  CHECK (check_out_at IS NULL OR check_out_at >= check_in_at)
) PARTITION BY RANGE (work_date);

CREATE TABLE attendance_default PARTITION OF attendance DEFAULT;
CREATE TABLE attendance_2026m09 PARTITION OF attendance FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE attendance_2026m10 PARTITION OF attendance FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');

CREATE INDEX attendance_employee_date_idx ON attendance (employee_id, work_date DESC);
CREATE INDEX attendance_status_idx ON attendance (organization_id, status) WHERE status = 'NEEDS_REVIEW';
CREATE INDEX attendance_location_gix ON attendance USING gist (location);
-- Satu kehadiran aktif per karyawan per hari; yang ditolak boleh diajukan ulang.
CREATE UNIQUE INDEX attendance_active_uidx ON attendance (employee_id, work_date) WHERE status <> 'REJECTED';

-- -----------------------------------------------------------------------------
-- Insiden / HSE dan lembur
-- -----------------------------------------------------------------------------
CREATE TABLE incident_report (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  work_plan_id    uuid NOT NULL REFERENCES work_plan(id) ON DELETE CASCADE,
  reported_by     uuid NOT NULL REFERENCES employee(id),
  occurred_on     date NOT NULL,
  category        incident_category NOT NULL,
  severity        incident_severity NOT NULL,
  description     text NOT NULL,
  status          incident_status NOT NULL DEFAULT 'OPEN',
  resolved_by     uuid REFERENCES employee(id),
  resolved_at     timestamptz,
  resolution_note text,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX incident_open_idx ON incident_report (organization_id, status) WHERE status <> 'RESOLVED';
CREATE INDEX incident_plan_idx ON incident_report (work_plan_id);

CREATE TABLE incident_evidence (
  incident_id uuid NOT NULL REFERENCES incident_report(id) ON DELETE CASCADE,
  file_id     uuid NOT NULL REFERENCES file_object(id),
  PRIMARY KEY (incident_id, file_id)
);

CREATE TABLE incident_event (                 -- jejak penanganan insiden
  id          uuid PRIMARY KEY DEFAULT new_id(),
  incident_id uuid NOT NULL REFERENCES incident_report(id) ON DELETE CASCADE,
  actor_id    uuid REFERENCES employee(id),
  note        text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE overtime_log (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  work_plan_id    uuid NOT NULL REFERENCES work_plan(id) ON DELETE CASCADE,
  plan_document_id uuid REFERENCES plan_document(id),  -- SK yang berlaku saat diajukan
  employee_id     uuid NOT NULL REFERENCES employee(id),
  work_date       date NOT NULL,
  hours           numeric(4,2) NOT NULL CHECK (hours > 0 AND hours <= 12),
  reason          text NOT NULL,
  status          approval_status NOT NULL DEFAULT 'PENDING_PM',
  reviewed_by     uuid REFERENCES employee(id),
  reviewed_at     timestamptz,
  review_note     text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  -- pengaju tidak boleh menyetujui pengajuannya sendiri
  CHECK (reviewed_by IS NULL OR reviewed_by <> employee_id)
);
CREATE INDEX overtime_recap_idx ON overtime_log (organization_id, work_date, status);
CREATE UNIQUE INDEX overtime_no_double_uidx ON overtime_log (employee_id, work_plan_id, work_date)
  WHERE status <> 'REJECTED';

-- -----------------------------------------------------------------------------
-- QR: token acak, hanya SHA-256-nya yang disimpan.
-- Pemindaian mencatat siapa, kapan, dan dari mana (titik lokasi PostGIS),
-- sehingga verifikasi tanda tangan dokumen punya jejak audit. Lihat 04_signature_auth.sql.
-- -----------------------------------------------------------------------------
CREATE TABLE qr_token (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  purpose         qr_purpose NOT NULL,
  subject_type    text NOT NULL,              -- 'plan_document' | 'asset' | 'site' | 'visitor'
  subject_id      uuid NOT NULL,
  token_sha256    bytea NOT NULL UNIQUE,      -- token mentah tidak pernah disimpan
  secret_version  smallint NOT NULL DEFAULT 1,
  site_id         uuid REFERENCES site(id),   -- bila pemindaian harus di lokasi tertentu
  allowed_radius_m integer,
  issued_by       uuid NOT NULL REFERENCES app_user(id),
  issued_at       timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz,
  max_scans       integer CHECK (max_scans IS NULL OR max_scans > 0),
  scan_count      integer NOT NULL DEFAULT 0,
  revoked_at      timestamptz,
  revoked_reason  text
);
CREATE INDEX qr_token_subject_idx ON qr_token (subject_type, subject_id);
CREATE INDEX qr_token_live_idx ON qr_token (organization_id, purpose)
  WHERE revoked_at IS NULL;

CREATE TABLE qr_scan (
  id            uuid NOT NULL DEFAULT new_id(),
  qr_token_id   uuid REFERENCES qr_token(id) ON DELETE SET NULL,
  scanned_at    timestamptz NOT NULL DEFAULT now(),
  scanned_by    uuid REFERENCES app_user(id),
  result        qr_scan_result NOT NULL,
  location      geography(Point,4326),
  distance_m    numeric(8,1),
  device_label  text,
  image_file_id uuid REFERENCES file_object(id),
  PRIMARY KEY (id, scanned_at)
) PARTITION BY RANGE (scanned_at);

CREATE TABLE qr_scan_default PARTITION OF qr_scan DEFAULT;
CREATE INDEX qr_scan_token_idx ON qr_scan (qr_token_id, scanned_at DESC);
CREATE INDEX qr_scan_location_gix ON qr_scan USING gist (location);

-- -----------------------------------------------------------------------------
-- Antrean luring: idempoten berdasarkan client_op_id dari perangkat
-- -----------------------------------------------------------------------------
CREATE TABLE offline_operation (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL REFERENCES app_user(id),
  device_id       text NOT NULL,
  client_op_id    uuid NOT NULL,              -- dibuat di perangkat sebelum dikirim
  op_type         text NOT NULL,
  payload         jsonb NOT NULL,
  client_created_at timestamptz NOT NULL,
  received_at     timestamptz NOT NULL DEFAULT now(),
  applied_at      timestamptz,
  status          sync_status NOT NULL DEFAULT 'PENDING',
  error_message   text,
  UNIQUE (user_id, client_op_id)              -- kirim ulang tidak menggandakan data
);
CREATE INDEX offline_pending_idx ON offline_operation (organization_id, status) WHERE status = 'PENDING';

-- -----------------------------------------------------------------------------
-- Audit: satu tabel untuk seluruh perubahan penting, dipartisi bulanan.
-- Isi payload sudah disaring di aplikasi agar tidak memuat data pribadi mentah.
-- -----------------------------------------------------------------------------
CREATE TABLE audit_event (
  id              uuid NOT NULL DEFAULT new_id(),
  organization_id uuid NOT NULL,
  occurred_at     timestamptz NOT NULL DEFAULT now(),
  actor_user_id   uuid,
  actor_label     text NOT NULL,
  action          text NOT NULL,
  entity_type     text NOT NULL,
  entity_id       uuid,
  work_plan_id    uuid,
  detail          text,
  changes         jsonb,
  PRIMARY KEY (id, occurred_at)
) PARTITION BY RANGE (occurred_at);

CREATE TABLE audit_event_default PARTITION OF audit_event DEFAULT;
CREATE INDEX audit_entity_idx ON audit_event (entity_type, entity_id, occurred_at DESC);
CREATE INDEX audit_plan_idx ON audit_event (work_plan_id, occurred_at DESC);
CREATE INDEX audit_actor_idx ON audit_event (actor_user_id, occurred_at DESC);
