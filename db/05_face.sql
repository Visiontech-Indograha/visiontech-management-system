-- =============================================================================
-- Visiontech VMS · Berkas 5 dari 5: pengenalan wajah untuk absensi (pgvector)
--
-- Data wajah adalah data biometrik. Perlakuannya berbeda dari data lain:
--   1. Yang disimpan adalah EMBEDDING (deretan angka), bukan foto. Foto acuan
--      hanya disimpan bila pengguna menyetujui, dan punya masa simpan terbatas.
--   2. Wajib ada persetujuan tertulis per karyawan, bisa ditarik kapan saja.
--      Menarik persetujuan langsung menonaktifkan seluruh embedding-nya.
--   3. Hanya HR, pemilik data, dan proses pencocokan yang boleh membacanya.
--      Peran pelaporan/BI tidak pernah diberi akses.
--   4. Embedding tidak bisa diubah setelah dibuat; perubahan berarti pendaftaran ulang.
--   5. Pencocokan wajah adalah BUKTI PENDUKUNG, bukan penentu tunggal. Hasil di
--      bawah ambang batas menandai absensi untuk diperiksa manusia, bukan menolaknya
--      diam-diam.
-- =============================================================================
SET search_path = vms, public;

CREATE TYPE face_check_result AS ENUM ('MATCH','NO_MATCH','LOW_QUALITY','NOT_ENROLLED','SKIPPED');
CREATE TYPE consent_state AS ENUM ('GRANTED','WITHDRAWN');

-- -----------------------------------------------------------------------------
-- Persetujuan pemakaian data biometrik
-- -----------------------------------------------------------------------------
CREATE TABLE biometric_consent (
  id             uuid PRIMARY KEY DEFAULT new_id(),
  employee_id    uuid NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
  state          consent_state NOT NULL,
  purpose_text   text NOT NULL,              -- kalimat persetujuan yang benar-benar dibaca karyawan
  policy_version text NOT NULL,
  recorded_by    uuid REFERENCES app_user(id),
  recorded_at    timestamptz NOT NULL DEFAULT now(),
  ip_address     inet
);
CREATE INDEX biometric_consent_emp_idx ON biometric_consent (employee_id, recorded_at DESC);

CREATE OR REPLACE FUNCTION has_biometric_consent(p_employee uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT COALESCE((
    SELECT state = 'GRANTED' FROM biometric_consent
    WHERE employee_id = p_employee ORDER BY recorded_at DESC LIMIT 1
  ), false)
$$;

-- -----------------------------------------------------------------------------
-- Pendaftaran wajah. Beberapa embedding per orang (sudut dan pencahayaan berbeda)
-- membuat pencocokan jauh lebih tahan terhadap kondisi lapangan.
-- Dimensi 512 mengikuti keluarga model ArcFace/InsightFace; sesuaikan bila
-- model Anda berbeda, dan JANGAN mencampur dua model dalam satu kolom.
-- -----------------------------------------------------------------------------
CREATE TABLE face_enrollment (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  employee_id     uuid NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
  embedding       vector(512) NOT NULL,       -- sudah dinormalisasi L2 oleh aplikasi
  model_name      text NOT NULL,              -- mis. 'arcface-r100'
  model_version   text NOT NULL,
  quality_score   numeric(4,3) CHECK (quality_score BETWEEN 0 AND 1),
  source_file_id  uuid REFERENCES file_object(id),   -- foto acuan; boleh NULL
  captured_at     timestamptz NOT NULL DEFAULT now(),
  enrolled_by     uuid REFERENCES app_user(id),
  is_active       boolean NOT NULL DEFAULT true,
  deactivated_at  timestamptz,
  deactivate_reason text
);
CREATE INDEX face_enrollment_employee_idx ON face_enrollment (employee_id) WHERE is_active;
-- Indeks vektor: cosine, cocok untuk embedding yang sudah dinormalisasi.
CREATE INDEX face_enrollment_vec_idx ON face_enrollment
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
COMMENT ON COLUMN face_enrollment.embedding IS 'Embedding wajah, bukan foto. Tidak dapat dikembalikan menjadi gambar aslinya, tetapi tetap data biometrik.';

-- Embedding bersifat tetap; yang boleh berubah hanya penonaktifan.
CREATE OR REPLACE FUNCTION tg_face_enrollment_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.embedding IS DISTINCT FROM OLD.embedding
     OR NEW.employee_id IS DISTINCT FROM OLD.employee_id
     OR NEW.model_name IS DISTINCT FROM OLD.model_name THEN
    RAISE EXCEPTION 'Embedding wajah tidak dapat diubah. Nonaktifkan lalu daftarkan ulang.'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER face_enrollment_immutable BEFORE UPDATE ON face_enrollment
  FOR EACH ROW EXECUTE FUNCTION tg_face_enrollment_immutable();
CREATE TRIGGER face_enrollment_audit AFTER INSERT OR UPDATE ON face_enrollment
  FOR EACH ROW EXECUTE FUNCTION tg_audit_row();

-- Pendaftaran hanya boleh jika persetujuan aktif.
CREATE OR REPLACE FUNCTION tg_face_requires_consent() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NOT has_biometric_consent(NEW.employee_id) THEN
    RAISE EXCEPTION 'Pendaftaran wajah membutuhkan persetujuan biometrik yang masih berlaku.'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER face_enrollment_consent BEFORE INSERT ON face_enrollment
  FOR EACH ROW EXECUTE FUNCTION tg_face_requires_consent();

-- Menarik persetujuan langsung mematikan seluruh embedding orang tersebut.
CREATE OR REPLACE FUNCTION tg_consent_withdrawn() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.state = 'WITHDRAWN' THEN
    UPDATE face_enrollment
       SET is_active = false, deactivated_at = now(), deactivate_reason = 'Persetujuan biometrik ditarik'
     WHERE employee_id = NEW.employee_id AND is_active;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER biometric_consent_withdraw AFTER INSERT ON biometric_consent
  FOR EACH ROW EXECUTE FUNCTION tg_consent_withdrawn();

-- -----------------------------------------------------------------------------
-- Riwayat pencocokan saat absensi. Embedding percobaan disimpan singkat
-- (untuk penyelidikan sengketa), lalu dibersihkan oleh purge_face_probes().
-- -----------------------------------------------------------------------------
CREATE TABLE face_check (
  id              uuid NOT NULL DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  checked_at      timestamptz NOT NULL DEFAULT now(),
  claimed_employee_id uuid NOT NULL REFERENCES employee(id),
  matched_employee_id uuid REFERENCES employee(id),
  matched_enrollment_id uuid REFERENCES face_enrollment(id),
  similarity      numeric(5,4),               -- 1 - jarak kosinus
  threshold_used  numeric(5,4) NOT NULL,
  result          face_check_result NOT NULL,
  liveness_score  numeric(4,3),               -- hasil pemeriksaan anti-spoof dari aplikasi
  probe_embedding vector(512),                -- dihapus setelah masa simpan berakhir
  probe_file_id   uuid REFERENCES file_object(id),
  attendance_id   uuid,                       -- diisi bila absensi berhasil dibuat
  attendance_event text NOT NULL DEFAULT 'CHECK_IN' CHECK (attendance_event IN ('CHECK_IN','CHECK_OUT')),
  device_label    text,
  PRIMARY KEY (id, checked_at)
) PARTITION BY RANGE (checked_at);
CREATE TABLE face_check_default PARTITION OF face_check DEFAULT;
CREATE INDEX face_check_employee_idx ON face_check (claimed_employee_id, checked_at DESC);
CREATE INDEX face_check_result_idx ON face_check (organization_id, result, checked_at DESC);

-- -----------------------------------------------------------------------------
-- Gambar wajah sementara + embedding yang dikirim HP saat absen (BUKAN foto absensi).
-- Dihapus sesuai organization.face_probe_retention_days oleh purge_face_probes().
-- -----------------------------------------------------------------------------
CREATE TABLE face_probe (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  employee_id     uuid NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
  created_at      timestamptz NOT NULL DEFAULT now(),
  embedding       vector(512),                       -- NULL = face-service sedang mati; diperiksa ulang kemudian
  model_name      text,
  model_version   text,
  quality_score   numeric(4,3) CHECK (quality_score BETWEEN 0 AND 1),
  liveness        jsonb NOT NULL DEFAULT '{}'::jsonb, -- tantangan & hasil dari aplikasi
  file_id         uuid REFERENCES file_object(id),   -- gambar wajah sementara; dihapus setelah masa simpan
  sha256          bytea NOT NULL,                    -- hash byte asli yang diterima server (dicocokkan dengan payload luring)
  consumed_at     timestamptz,
  consumed_event  text CHECK (consumed_event IN ('CHECK_IN', 'CHECK_OUT')),
  attendance_id   uuid
);
CREATE INDEX face_probe_employee_idx ON face_probe (employee_id, created_at DESC);

-- Ambang batas disimpan sebagai data agar bisa dikalibrasi tanpa rilis ulang.
ALTER TABLE organization
  ADD COLUMN face_match_threshold numeric(5,4) NOT NULL DEFAULT 0.6500
    CHECK (face_match_threshold BETWEEN 0.3 AND 0.99),
  ADD COLUMN face_liveness_required boolean NOT NULL DEFAULT true,
  ADD COLUMN face_probe_retention_days integer NOT NULL DEFAULT 30
    CHECK (face_probe_retention_days BETWEEN 1 AND 365);
COMMENT ON COLUMN organization.face_match_threshold IS
  'Ambang kemiripan kosinus. 0,65 adalah titik awal yang wajar untuk model 512 dimensi, WAJIB dikalibrasi dengan data nyata (ukur FAR dan FRR) sebelum dipakai di lapangan.';

-- -----------------------------------------------------------------------------
-- Pencocokan. Mengembalikan kandidat terbaik beserta kemiripannya.
-- Pencarian dibatasi pada karyawan aktif di organisasi yang sama.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_face(
  p_org uuid, p_embedding vector(512), p_limit integer DEFAULT 5
) RETURNS TABLE (employee_id uuid, enrollment_id uuid, full_name text, similarity numeric)
LANGUAGE sql STABLE AS $$
  SELECT f.employee_id, f.id, e.full_name,
         round((1 - (f.embedding <=> p_embedding))::numeric, 4) AS similarity
  FROM face_enrollment f
  JOIN employee e ON e.id = f.employee_id
  WHERE f.organization_id = p_org
    AND f.is_active
    AND e.is_active
    AND e.deleted_at IS NULL
  ORDER BY f.embedding <=> p_embedding
  LIMIT p_limit
$$;

-- Kemiripan tertinggi dengan karyawan LAIN (tanpa menyebut siapa): untuk menolak pendaftaran wajah yang sudah dipakai.
CREATE OR REPLACE FUNCTION face_best_other_similarity(p_org uuid, p_employee uuid, p_embedding vector(512))
RETURNS numeric
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = vms, public AS $$
  SELECT max(round((1 - (f.embedding <=> p_embedding))::numeric, 4))
    FROM face_enrollment f
    JOIN employee e ON e.id = f.employee_id
   WHERE f.organization_id = p_org AND f.is_active AND e.is_active AND e.deleted_at IS NULL
     AND f.employee_id <> p_employee
     AND p_org = current_org_id()
$$;

-- Verifikasi 1:1 saat absensi: "apakah wajah ini benar-benar orang yang mengaku?"
-- Dipakai aplikasi sebelum membuat baris attendance.
CREATE OR REPLACE FUNCTION verify_face_for_attendance(
  p_org uuid,
  p_claimed_employee uuid,
  p_embedding vector(512),
  p_liveness numeric DEFAULT NULL,
  p_probe_file uuid DEFAULT NULL,
  p_device text DEFAULT NULL,
  p_event text DEFAULT 'CHECK_IN'
) RETURNS TABLE (result face_check_result, similarity numeric, threshold numeric, matched_employee uuid, note text,
                 check_id uuid)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = vms, public AS $$
DECLARE
  v_org organization%ROWTYPE;
  v_best_emp uuid;
  v_emp uuid;
  v_enr uuid;
  v_sim numeric;
  v_result face_check_result;
  v_note text;
  v_check uuid;
BEGIN
  -- DEFINER melewati RLS: pastikan pemanggil hanya memeriksa dirinya sendiri (HR/ADMIN boleh untuk pemeriksaan ulang).
  IF p_org IS DISTINCT FROM current_org_id() THEN
    RAISE EXCEPTION 'Organisasi tidak sesuai.' USING ERRCODE = '42501';
  END IF;
  IF p_claimed_employee IS DISTINCT FROM (SELECT employee_id FROM app_user WHERE id = current_user_id())
     AND NOT (has_role('ADMIN') OR has_role('HR')) THEN
    RAISE EXCEPTION 'Pencocokan wajah hanya untuk diri sendiri.' USING ERRCODE = '42501';
  END IF;
  IF p_event NOT IN ('CHECK_IN', 'CHECK_OUT') THEN
    RAISE EXCEPTION 'Jenis absensi tidak dikenal.' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_org FROM organization WHERE id = p_org;

  IF NOT has_biometric_consent(p_claimed_employee) THEN
    v_result := 'SKIPPED';
    v_note := 'Karyawan belum menyetujui pemakaian data wajah. Absensi dilanjutkan tanpa pencocokan wajah.';
  ELSIF NOT EXISTS (SELECT 1 FROM face_enrollment WHERE employee_id = p_claimed_employee AND is_active) THEN
    v_result := 'NOT_ENROLLED';
    v_note := 'Wajah belum terdaftar. Minta karyawan melakukan pendaftaran wajah.';
  ELSIF v_org.face_liveness_required AND (p_liveness IS NULL OR p_liveness < 0.5) THEN
    v_result := 'LOW_QUALITY';
    v_note := 'Pemeriksaan keaslian wajah (anti-foto) tidak lolos. Coba ulangi di tempat yang lebih terang.';
  ELSE
    -- kemiripan terhadap orang yang mengaku
    SELECT mf.employee_id, mf.enrollment_id, mf.similarity INTO v_emp, v_enr, v_sim
      FROM match_face(p_org, p_embedding, 50) mf WHERE mf.employee_id = p_claimed_employee LIMIT 1;
    -- kandidat terbaik secara keseluruhan, untuk mendeteksi orang lain yang lebih mirip
    SELECT mf.employee_id INTO v_best_emp FROM match_face(p_org, p_embedding, 1) mf;

    IF v_sim IS NULL OR v_sim < v_org.face_match_threshold THEN
      v_result := 'NO_MATCH';
      v_note := 'Wajah tidak cocok dengan data karyawan tersebut. Absensi ditandai untuk diperiksa.';
    ELSIF v_best_emp IS DISTINCT FROM p_claimed_employee THEN
      v_result := 'NO_MATCH';
      v_note := 'Wajah lebih menyerupai karyawan lain. Absensi ditandai untuk diperiksa.';
    ELSE
      v_result := 'MATCH';
      v_note := 'Wajah cocok dengan data karyawan.';
    END IF;
  END IF;

  INSERT INTO face_check (organization_id, claimed_employee_id, matched_employee_id, matched_enrollment_id,
                          similarity, threshold_used, result, liveness_score, probe_embedding, probe_file_id,
                          device_label, attendance_event)
  VALUES (p_org, p_claimed_employee, v_emp, v_enr,
          v_sim, v_org.face_match_threshold, v_result, p_liveness, p_embedding, p_probe_file,
          p_device, p_event)
  RETURNING id INTO v_check;

  RETURN QUERY SELECT v_result, v_sim, v_org.face_match_threshold, v_emp, v_note, v_check;
END $$;

-- Absensi yang gagal cocok wajah tidak ditolak diam-diam, melainkan masuk antrean
-- pemeriksaan Finance, sama seperti absensi di luar radius.
ALTER TABLE attendance
  ADD COLUMN face_check_id uuid,
  ADD COLUMN face_similarity numeric(5,4),
  ADD COLUMN face_result face_check_result;

-- Pengenalan wajah saat absen pulang (tanpa foto bukti pulang).
ALTER TABLE attendance
  ADD COLUMN check_out_face_check_id uuid,
  ADD COLUMN check_out_face_result face_check_result,
  ADD COLUMN check_out_face_similarity numeric(5,4);

CREATE OR REPLACE FUNCTION tg_attendance_face_flag() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.face_result IN ('NO_MATCH','LOW_QUALITY') THEN
    NEW.status := 'NEEDS_REVIEW';
  END IF;
  RETURN NEW;
END $$;
-- Trigger BEFORE dijalankan menurut urutan nama: nama ini harus diurutkan SETELAH
-- `attendance_geofence`, karena geofence menyetel ulang status dari jarak (migrasi 0003).
CREATE TRIGGER attendance_post_geofence_face_flag BEFORE INSERT ON attendance
  FOR EACH ROW EXECUTE FUNCTION tg_attendance_face_flag();

-- -----------------------------------------------------------------------------
-- Masa simpan: embedding percobaan dihapus setelah lewat batas retensi.
-- Jalankan harian (pg_cron). Hasil pencocokan tetap tersimpan sebagai bukti audit.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION purge_face_probes() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = vms, public AS $$
DECLARE v_files uuid[]; v_checks integer := 0; v_probes integer := 0;
BEGIN
  -- Hanya HR/ADMIN (penjadwal memakai token ADMIN) yang boleh membersihkan.
  IF NOT (has_role('ADMIN') OR has_role('HR')) THEN
    RAISE EXCEPTION 'Pembersihan data wajah hanya untuk HR/ADMIN.' USING ERRCODE = '42501';
  END IF;
  -- Gambar yang sudah lewat masa simpan (objek MinIO-nya dihapus aplikasi lebih dulu).
  SELECT COALESCE(array_agg(e.file_id), '{}') INTO v_files FROM expired_face_probe_files() e;

  -- Gambar yang sama dirujuk face_probe dan face_check: lepaskan rujukan face_check dulu.
  WITH cleaned AS (
    UPDATE face_check fc
       SET probe_embedding = NULL, probe_file_id = NULL
      FROM organization o
     WHERE o.id = fc.organization_id
       AND (fc.probe_embedding IS NOT NULL OR fc.probe_file_id IS NOT NULL)
       AND (fc.checked_at < now() - make_interval(days => o.face_probe_retention_days)
            OR fc.probe_file_id = ANY (v_files))
    RETURNING 1
  )
  SELECT count(*) INTO v_checks FROM cleaned;

  WITH gone AS (
    DELETE FROM face_probe fp
     USING organization o
     WHERE o.id = fp.organization_id
       AND fp.created_at < now() - make_interval(days => o.face_probe_retention_days)
    RETURNING 1
  )
  SELECT count(*) INTO v_probes FROM gone;

  DELETE FROM file_object fo
   WHERE fo.id = ANY (v_files)
     AND NOT EXISTS (SELECT 1 FROM face_probe fp WHERE fp.file_id = fo.id)
     AND NOT EXISTS (SELECT 1 FROM face_check fc WHERE fc.probe_file_id = fo.id);
  RETURN v_checks + v_probes;
END $$;

-- Kunci objek MinIO untuk gambar wajah yang sudah lewat masa simpan: dihapus aplikasi SEBELUM purge_face_probes().
CREATE OR REPLACE FUNCTION expired_face_probe_files() RETURNS TABLE (file_id uuid, storage_key text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = vms, public AS $$
BEGIN
  IF NOT (has_role('ADMIN') OR has_role('HR')) THEN
    RAISE EXCEPTION 'Hanya HR/ADMIN.' USING ERRCODE = '42501';
  END IF;
  RETURN QUERY
    SELECT fo.id, fo.storage_key
      FROM file_object fo
     WHERE fo.id IN (
             SELECT fp.file_id FROM face_probe fp JOIN organization o ON o.id = fp.organization_id
              WHERE fp.file_id IS NOT NULL
                AND fp.created_at < now() - make_interval(days => o.face_probe_retention_days)
             UNION
             SELECT fc.probe_file_id FROM face_check fc JOIN organization o ON o.id = fc.organization_id
              WHERE fc.probe_file_id IS NOT NULL
                AND fc.checked_at < now() - make_interval(days => o.face_probe_retention_days));
END $$;

-- -----------------------------------------------------------------------------
-- Keamanan: biometrik hanya untuk pemilik data, HR, dan proses pencocokan.
-- Peran pelaporan tidak pernah diberi hak baca.
-- -----------------------------------------------------------------------------
ALTER TABLE face_enrollment   ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_check        ENABLE ROW LEVEL SECURITY;
ALTER TABLE biometric_consent ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_probe        ENABLE ROW LEVEL SECURITY;

CREATE POLICY face_enrollment_visibility ON face_enrollment
USING (
  organization_id = current_org_id() AND (
    has_role('HR') OR has_role('ADMIN')
    OR employee_id = (SELECT employee_id FROM app_user WHERE id = current_user_id())
  )
);
CREATE POLICY face_check_visibility ON face_check
USING (
  organization_id = current_org_id() AND (
    has_role('HR') OR has_role('ADMIN') OR has_role('FINANCE')
    OR claimed_employee_id = (SELECT employee_id FROM app_user WHERE id = current_user_id())
  )
);
CREATE POLICY biometric_consent_visibility ON biometric_consent
USING (
  has_role('HR') OR has_role('ADMIN')
  OR employee_id = (SELECT employee_id FROM app_user WHERE id = current_user_id())
);

CREATE POLICY face_probe_visibility ON face_probe
USING (
  organization_id = current_org_id() AND (
    has_role('HR') OR has_role('ADMIN')
    OR employee_id = (SELECT employee_id FROM app_user WHERE id = current_user_id())
  )
);

GRANT SELECT, INSERT, UPDATE ON face_enrollment, face_check, biometric_consent, face_probe TO vms_app;
REVOKE ALL ON face_enrollment, face_check, biometric_consent, face_probe FROM vms_readonly;

-- Indeks kolom foreign key (Alembic 0021_fk_indexes). Tabel berpartisi cukup diindeks di induknya.
CREATE INDEX IF NOT EXISTS ix_biometric_consent_recorded_by ON biometric_consent (recorded_by);
CREATE INDEX IF NOT EXISTS ix_face_check_matched_employee_id ON face_check (matched_employee_id);
CREATE INDEX IF NOT EXISTS ix_face_check_matched_enrollment_id ON face_check (matched_enrollment_id);
CREATE INDEX IF NOT EXISTS ix_face_enrollment_source_file_id ON face_enrollment (source_file_id);
CREATE INDEX IF NOT EXISTS ix_face_enrollment_enrolled_by ON face_enrollment (enrolled_by);
CREATE INDEX IF NOT EXISTS ix_face_enrollment_organization_id ON face_enrollment (organization_id);
CREATE INDEX IF NOT EXISTS ix_face_check_probe_file_id ON face_check (probe_file_id);
CREATE INDEX IF NOT EXISTS ix_face_probe_organization_id ON face_probe (organization_id);
CREATE INDEX IF NOT EXISTS ix_face_probe_file_id ON face_probe (file_id);

-- -----------------------------------------------------------------------------
-- Peran runtime API (Alembic 0024_runtime_role, P9-2): bukan superuser, bukan pemilik, tanpa BYPASSRLS, sehingga
-- RLS berlaku. Ditaruh di berkas terakhir karena hak akses mencakup semua tabel. Sandi diatur di luar berkas ini.
-- -----------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
    CREATE ROLE vms_api LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END $$;
-- Logout mencabut sesi dari token mentah, sebelum identitas pengguna diketahui.
CREATE OR REPLACE FUNCTION vms.revoke_session_by_token(p_raw_refresh text, p_reason text) RETURNS void
LANGUAGE sql SET search_path = vms, public AS $fn$
  UPDATE user_session SET state = 'REVOKED', revoked_at = now(), revoked_reason = p_reason
   WHERE refresh_sha256 = digest(p_raw_refresh, 'sha256') AND state = 'ACTIVE';
$fn$;
-- Pemeriksaan SIM pengemudi saat PM/OPS menyusun SK: dokumen pribadi tetap tertutup (hanya pemilik & HR yang
-- melihat barisnya), yang keluar hanya id karyawan yang lolos — padanan trigger tg_vehicle_driver_licence.
CREATE OR REPLACE FUNCTION vms.employees_with_valid_licence(p_ids uuid[], p_licence text, p_until date)
RETURNS SETOF uuid LANGUAGE sql STABLE SET search_path = vms, public AS $fn$
  SELECT DISTINCT d.employee_id FROM employee_document d JOIN employee e ON e.id = d.employee_id
   WHERE d.employee_id = ANY(p_ids) AND e.organization_id = current_org_id()
     AND d.doc_type = p_licence AND d.lifecycle = 'CURRENT' AND (d.expiry_date IS NULL OR d.expiry_date >= p_until);
$fn$;
-- Fungsi basis data menegakkan aturan yang harus melihat SELURUH data organisasi (bentrok personel lintas unit,
-- SIM, verifikasi QR publik, sesi saat login/refresh, partisi bulanan, pembantu kebijakan yang membaca tabel
-- ber-RLS — tanpa ini work_plan → is_plan_leader → work_plan berulang tanpa akhir). Semuanya berjalan sebagai
-- pemilik (SECURITY DEFINER) dengan search_path tetap; hanya pembaca konteks murni yang tetap sebagai pemanggil.
DO $$
DECLARE f regprocedure;
BEGIN
  FOR f IN SELECT p.oid::regprocedure FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'vms' AND p.prokind = 'f'
              AND p.proname NOT IN ('current_org_id', 'current_user_id', 'new_id') LOOP
    EXECUTE format('ALTER FUNCTION %s SECURITY DEFINER SET search_path = vms, public', f);
  END LOOP;
END $$;
-- Batas RLS = tenant. Pembatasan per unit/keterlibatan ditegakkan di service (calon ketua pengganti, 403 vs 404,
-- Finance/HR untuk rekap, ASSET untuk insiden aset) dan diuji matriks RBAC; kebijakan lama lebih sempit dari aturan
-- itu (tak pernah berlaku karena RLS terlewati). Dokumen pribadi, sesi, antrean luring, dan data wajah tetap
-- dibatasi per orang.
ALTER POLICY work_plan_visibility ON vms.work_plan USING (organization_id = vms.current_org_id());
ALTER POLICY attendance_visibility ON vms.attendance USING (organization_id = vms.current_org_id());
ALTER POLICY incident_visibility ON vms.incident_report USING (organization_id = vms.current_org_id());
ALTER POLICY overtime_visibility ON vms.overtime_log USING (organization_id = vms.current_org_id());
ALTER POLICY qr_token_visibility ON vms.qr_token USING (organization_id = vms.current_org_id());
-- signing_key hanya menyimpan KUNCI PUBLIK (kunci privat di env/KMS): PM yang menerbitkan SK harus bisa membaca &
-- mendaftarkan kunci organisasinya.
ALTER POLICY signing_key_visibility ON vms.signing_key USING (organization_id = vms.current_org_id());
GRANT USAGE ON SCHEMA vms TO vms_api;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA vms TO vms_api;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA vms TO vms_api;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA vms TO vms_api;
GRANT DELETE ON vms.work_plan_attachment, vms.work_plan_task_attachment, vms.work_plan_day, vms.work_plan_task,
                vms.work_plan_member, vms.report_evidence, vms.member_report_evidence, vms.final_report_evidence,
                vms.user_session
   TO vms_api;
REVOKE UPDATE, DELETE ON vms.audit_event FROM vms_api;
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'vms' AND c.relkind = 'r' AND c.relispartition LOOP
    EXECUTE format('REVOKE ALL ON vms.%I FROM vms_api', r.relname);
  END LOOP;
END $$;

-- RLS batas tenant untuk tabel ber-organization_id yang tersisa (Alembic 0025_rls_remaining_tables). app_user sengaja
-- tanpa RLS: login & rotasi token mencari akun sebelum identitas/organisasi diketahui.
ALTER TABLE vms.site ENABLE ROW LEVEL SECURITY;
CREATE POLICY site_isolation ON vms.site USING (organization_id = vms.current_org_id());
ALTER TABLE vms.file_object ENABLE ROW LEVEL SECURITY;
CREATE POLICY file_object_isolation ON vms.file_object USING (organization_id = vms.current_org_id());
ALTER TABLE vms.notification ENABLE ROW LEVEL SECURITY;
CREATE POLICY notification_isolation ON vms.notification USING (organization_id = vms.current_org_id());
ALTER TABLE vms.attendance_device_key ENABLE ROW LEVEL SECURITY;
CREATE POLICY attendance_device_key_isolation ON vms.attendance_device_key USING (organization_id = vms.current_org_id());
ALTER TABLE vms.attendance_offline_event ENABLE ROW LEVEL SECURITY;
CREATE POLICY attendance_offline_event_isolation ON vms.attendance_offline_event USING (organization_id = vms.current_org_id());
ALTER TABLE vms.signature_serial_counter ENABLE ROW LEVEL SECURITY;
CREATE POLICY signature_serial_counter_isolation ON vms.signature_serial_counter USING (organization_id = vms.current_org_id());

-- Riwayat revisi rencana kerja (Alembic 0027_plan_revision): insert-only untuk vms_api.
REVOKE UPDATE ON vms.plan_revision FROM vms_api;
ALTER TABLE vms.plan_revision ENABLE ROW LEVEL SECURITY;
CREATE POLICY plan_revision_isolation ON vms.plan_revision USING (organization_id = vms.current_org_id());

-- Jenis pekerjaan + template foto (Alembic 0029_work_type_photo): hak penuh + RLS tenant.
GRANT DELETE ON vms.work_type, vms.work_type_photo TO vms_api;
ALTER TABLE vms.work_type ENABLE ROW LEVEL SECURITY;
CREATE POLICY work_type_isolation ON vms.work_type USING (organization_id = vms.current_org_id());
ALTER TABLE vms.work_type_photo ENABLE ROW LEVEL SECURITY;
CREATE POLICY work_type_photo_isolation ON vms.work_type_photo USING (organization_id = vms.current_org_id());
