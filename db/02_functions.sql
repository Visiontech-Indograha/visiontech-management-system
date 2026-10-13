-- =============================================================================
-- Visiontech VMS · Berkas 2 dari 5: fungsi, trigger, dan tampilan (view)
-- Aturan yang tidak boleh dilanggar ditegakkan di sini, bukan hanya di aplikasi.
-- =============================================================================
SET search_path = vms, public;

-- -----------------------------------------------------------------------------
-- Konteks sesi. Aplikasi menyetel ini sekali per koneksi/transaksi:
--   SET LOCAL app.user_id = '...'; SET LOCAL app.organization_id = '...';
-- Dipakai oleh audit dan Row Level Security.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION current_user_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('app.user_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION current_org_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('app.organization_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION has_role(p_role role_code, p_unit uuid DEFAULT NULL) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_role ur
    WHERE ur.user_id = current_user_id()
      AND ur.role = p_role
      AND (ur.unit_id IS NULL OR p_unit IS NULL OR ur.unit_id = p_unit)
  )
$$;

-- Kewenangan mengikuti penugasan: siapa pun yang tercatat sebagai ketua pada SK
-- yang berlaku bertindak sebagai ketua untuk pekerjaan itu.
CREATE OR REPLACE FUNCTION is_plan_leader(p_plan uuid, p_user uuid DEFAULT current_user_id()) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM work_plan wp
    JOIN app_user u ON u.employee_id = wp.leader_employee_id
    WHERE wp.id = p_plan AND u.id = p_user
  )
$$;

CREATE OR REPLACE FUNCTION is_plan_member(p_plan uuid, p_user uuid DEFAULT current_user_id()) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM work_plan_member m
    JOIN app_user u ON u.employee_id = m.employee_id
    WHERE m.work_plan_id = p_plan AND u.id = p_user AND upper_inf(m.valid_period)
  )
$$;

-- -----------------------------------------------------------------------------
-- Trigger umum
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION tg_set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END $$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['organization','employee','app_user','work_plan','asset','daily_report'] LOOP
    EXECUTE format('CREATE TRIGGER %1$s_touch BEFORE UPDATE ON %1$s FOR EACH ROW EXECUTE FUNCTION tg_set_updated_at()', t);
  END LOOP;
END $$;

-- Penguncian optimistis: setiap UPDATE work_plan menaikkan row_version, dan
-- aplikasi wajib mengirim row_version yang dibacanya (cek di layer API).
CREATE OR REPLACE FUNCTION tg_bump_row_version() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.row_version = OLD.row_version THEN
    NEW.row_version := OLD.row_version + 1;
  ELSIF NEW.row_version <> OLD.row_version + 1 THEN
    RAISE EXCEPTION 'Data berubah di sesi lain. Muat ulang sebelum menyimpan.'
      USING ERRCODE = '40001';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER work_plan_row_version BEFORE UPDATE ON work_plan
  FOR EACH ROW EXECUTE FUNCTION tg_bump_row_version();

-- Audit generik: dipasang pada tabel yang perubahannya harus bisa ditelusuri.
CREATE OR REPLACE FUNCTION tg_audit_row() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  v_row jsonb;
  v_org uuid;
  v_plan uuid;
  v_changes jsonb;
BEGIN
  -- COALESCE tidak dapat dipakai pada tipe record, jadi barisnya dipilih eksplisit.
  v_row := CASE WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;
  v_plan := NULLIF(v_row ->> 'work_plan_id', '')::uuid;
  -- Organisasi dari data baris itu sendiri; konteks sesi hanya cadangan terakhir (V-15).
  v_org := COALESCE(
    NULLIF(v_row ->> 'organization_id', '')::uuid,
    (SELECT wp.organization_id FROM work_plan wp WHERE wp.id = v_plan),
    (SELECT e.organization_id FROM employee e WHERE e.id = NULLIF(v_row ->> 'employee_id', '')::uuid),
    (SELECT a.organization_id FROM asset a WHERE a.id = NULLIF(v_row ->> 'asset_id', '')::uuid),
    current_org_id()
  );

  IF TG_OP = 'UPDATE' THEN
    SELECT jsonb_object_agg(key, jsonb_build_object('dari', old_value, 'menjadi', new_value))
      INTO v_changes
    FROM (
      SELECT o.key, o.value AS old_value, n.value AS new_value
      FROM jsonb_each(to_jsonb(OLD)) o
      JOIN jsonb_each(to_jsonb(NEW)) n USING (key)
      WHERE o.value IS DISTINCT FROM n.value
    ) diff;
  END IF;

  INSERT INTO audit_event (organization_id, actor_user_id, actor_label, action, entity_type, entity_id, work_plan_id, changes)
  VALUES (
    v_org,
    current_user_id(),
    COALESCE(current_setting('app.actor_label', true), 'sistem'),
    TG_OP,
    TG_TABLE_NAME,
    (v_row ->> 'id')::uuid,
    v_plan,
    v_changes
  );
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['work_plan','plan_document','plan_change','employee_document','asset_allocation','incident_report','overtime_log','qr_token'] LOOP
    EXECUTE format('CREATE TRIGGER %1$s_audit AFTER INSERT OR UPDATE OR DELETE ON %1$s FOR EACH ROW EXECUTE FUNCTION tg_audit_row()', t);
  END LOOP;
END $$;

-- -----------------------------------------------------------------------------
-- Dokumen SK: isi tidak boleh diubah setelah terbit.
-- Hanya status penerimaan yang boleh berpindah, dan versi lama otomatis terkunci.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION tg_plan_document_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  -- Isi dokumen terbit tidak pernah berubah; hanya siklusnya (status) yang bergerak (R4).
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.work_plan_id IS DISTINCT FROM OLD.work_plan_id
     OR NEW.kind IS DISTINCT FROM OLD.kind
     OR NEW.version IS DISTINCT FROM OLD.version
     OR NEW.number IS DISTINCT FROM OLD.number
     OR NEW.snapshot IS DISTINCT FROM OLD.snapshot
     OR NEW.snapshot_sha256 IS DISTINCT FROM OLD.snapshot_sha256
     OR NEW.reason IS DISTINCT FROM OLD.reason
     OR NEW.issued_by IS DISTINCT FROM OLD.issued_by
     OR NEW.issued_at IS DISTINCT FROM OLD.issued_at
     -- penerimaan dicatat sekali: dari kosong ke terisi, tidak ditimpa sesudahnya
     OR (OLD.accepted_by IS NOT NULL AND NEW.accepted_by IS DISTINCT FROM OLD.accepted_by)
     OR (OLD.accepted_at IS NOT NULL AND NEW.accepted_at IS DISTINCT FROM OLD.accepted_at) THEN
    RAISE EXCEPTION 'Dokumen terbit bersifat tetap. Terbitkan versi baru, jangan mengubah versi lama.'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER plan_document_immutable BEFORE UPDATE ON plan_document
  FOR EACH ROW EXECUTE FUNCTION tg_plan_document_immutable();

CREATE OR REPLACE FUNCTION tg_final_report_locked() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  -- Laporan akhir yang disetujui adalah dokumen bertanda tangan (R-19): isinya tidak pernah berubah
  -- (UPDATE ditolak; hapus berantai data organisasi tetap boleh — yang ditandatangani adalah snapshot).
  IF TG_TABLE_NAME = 'final_report' THEN
    IF OLD.status = 'APPROVED' THEN
      RAISE EXCEPTION 'Laporan akhir yang sudah disetujui tidak dapat diubah.' USING ERRCODE = '23514';
    END IF;
  ELSIF EXISTS (SELECT 1 FROM final_report
                WHERE work_plan_id = NEW.work_plan_id AND status = 'APPROVED') THEN
    RAISE EXCEPTION 'Laporan akhir yang sudah disetujui tidak dapat diubah.' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER final_report_locked BEFORE UPDATE ON final_report
  FOR EACH ROW EXECUTE FUNCTION tg_final_report_locked();
CREATE TRIGGER final_report_evidence_locked BEFORE INSERT OR UPDATE ON final_report_evidence
  FOR EACH ROW EXECUTE FUNCTION tg_final_report_locked();

CREATE OR REPLACE FUNCTION tg_plan_document_hash() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.snapshot_sha256 := digest(NEW.snapshot::text, 'sha256');
  RETURN NEW;
END $$;
CREATE TRIGGER plan_document_hash BEFORE INSERT ON plan_document
  FOR EACH ROW EXECUTE FUNCTION tg_plan_document_hash();

-- Versi lama terkunci: turunan, tidak disimpan sebagai kolom agar tidak bisa basi.
CREATE OR REPLACE FUNCTION document_is_locked(p_document uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM plan_document newer
    JOIN plan_document d ON d.id = p_document AND newer.work_plan_id = d.work_plan_id
    WHERE newer.version > d.version
  )
$$;

-- -----------------------------------------------------------------------------
-- Absensi: jarak dihitung di basis data, bukan dipercayakan ke perangkat.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION tg_attendance_geofence() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  v_site   site%ROWTYPE;
  v_org    organization%ROWTYPE;
  v_radius integer;
BEGIN
  SELECT * INTO v_org FROM organization WHERE id = NEW.organization_id;
  SELECT * INTO v_site FROM site WHERE id = NEW.site_id;
  v_radius := COALESCE(v_site.radius_m, v_org.geofence_radius_m, 100);
  NEW.radius_m := v_radius;

  IF NEW.source = 'MACHINE' THEN
    NEW.distance_m := 0;
    NEW.location := NULL;
  ELSIF NEW.location IS NOT NULL AND v_site.id IS NOT NULL THEN
    -- Jarak dihitung ulang dari koordinat; nilai kiriman perangkat diabaikan.
    NEW.distance_m := round(ST_Distance(NEW.location, v_site.location)::numeric, 1);
  END IF;

  NEW.status := CASE WHEN NEW.distance_m > v_radius THEN 'NEEDS_REVIEW'::attendance_status
                     ELSE 'AUTO_VALID'::attendance_status END;

  -- R-33: swafoto wajib di luar radius untuk absen HP maupun web (mesin absen dikecualikan).
  IF NEW.status = 'NEEDS_REVIEW' AND NEW.source IN ('MOBILE','WEB') AND NEW.selfie_file_id IS NULL THEN
    RAISE EXCEPTION 'Di luar radius toleransi (% m > % m): swafoto wajib dilampirkan.', NEW.distance_m, v_radius
      USING ERRCODE = '23514';
  END IF;

  NEW.is_late := (NEW.check_in_at AT TIME ZONE v_org.timezone)::time > v_org.shift_start;
  RETURN NEW;
END $$;
CREATE TRIGGER attendance_geofence BEFORE INSERT ON attendance
  FOR EACH ROW EXECUTE FUNCTION tg_attendance_geofence();

-- Kategori Dalam/Luar kota dari jarak titik absen ke pusat kota organisasi (Alembic 0035). NULL bila pusat kota
-- belum diatur atau absen tanpa titik; pemanggil lalu memakai attendance_city_category (rencana bertanda luar kota).
CREATE OR REPLACE FUNCTION attendance_city_category_at(p_org uuid, p_location geography) RETURNS text
LANGUAGE sql STABLE AS $$
  SELECT CASE WHEN ST_Distance(p_location, o.city_center) > o.city_radius_km * 1000.0
              THEN 'LUAR_KOTA' ELSE 'DALAM_KOTA' END
  FROM organization o
  WHERE o.id = p_org AND o.id = current_org_id() AND o.city_center IS NOT NULL AND p_location IS NOT NULL
$$;

CREATE OR REPLACE FUNCTION tg_attendance_checkout() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = vms, public AS $$
DECLARE
  v_org    organization%ROWTYPE;
  v_dist   numeric;
  v_radius integer;
BEGIN
  IF NEW.check_out_at IS NOT NULL AND OLD.check_out_at IS NULL THEN
    SELECT * INTO v_org FROM organization WHERE id = NEW.organization_id;
    NEW.is_early_leave := (NEW.check_out_at AT TIME ZONE v_org.timezone)::time < v_org.shift_end;
    IF NEW.check_out_location IS NOT NULL THEN
      -- Jarak dihitung ulang dari koordinat (nilai perangkat diabaikan) ke lokasi sah TERDEKAT: lokasi absen masuk,
      -- kantor, atau lokasi hari ini dari rencana kerja berjalan yang menugaskan karyawan ini.
      SELECT c.dist, c.radius INTO v_dist, v_radius
      FROM (
        SELECT ST_Distance(NEW.check_out_location, s.location)::numeric AS dist,
               CASE WHEN s.id = NEW.site_id THEN NEW.radius_m ELSE COALESCE(s.radius_m, NEW.radius_m) END AS radius
        FROM site s
        WHERE s.organization_id = NEW.organization_id
          AND (s.id = NEW.site_id
               OR (s.deleted_at IS NULL AND s.unit_id IS NULL)
               OR (s.deleted_at IS NULL AND s.id IN (
                     SELECT COALESCE(d.site_id, wp.site_id)
                     FROM work_plan wp
                     JOIN work_plan_day d ON d.work_plan_id = wp.id
                     JOIN work_plan_member m ON m.work_plan_id = wp.id AND m.employee_id = NEW.employee_id
                     WHERE wp.organization_id = NEW.organization_id
                       AND wp.status = 'IN_PROGRESS'
                       AND d.work_date = (NEW.check_out_at AT TIME ZONE v_org.timezone)::date
                       AND m.valid_period @> d.work_date
                       AND (NOT EXISTS (SELECT 1 FROM work_plan_day_member dm WHERE dm.work_plan_day_id = d.id)
                            OR EXISTS (SELECT 1 FROM work_plan_day_member dm
                                       WHERE dm.work_plan_day_id = d.id AND dm.employee_id = NEW.employee_id)))))
      ) c
      ORDER BY (c.dist - c.radius)
      LIMIT 1;
      IF v_dist IS NOT NULL THEN
        NEW.check_out_distance_m := round(v_dist, 1);
        NEW.check_out_outside := v_dist > v_radius;
      END IF;
      IF NEW.check_out_outside THEN
        IF COALESCE(current_setting('app.relax_checkout', true), '') <> 'on' AND NEW.source IN ('MOBILE','WEB') THEN
          IF NEW.check_out_selfie_file_id IS NULL THEN
            RAISE EXCEPTION 'Pulang di luar radius toleransi (% m > % m): swafoto wajib dilampirkan.',
              NEW.check_out_distance_m, v_radius USING ERRCODE = '23514';
          END IF;
          IF NEW.check_out_explanation IS NULL OR btrim(NEW.check_out_explanation) = '' THEN
            RAISE EXCEPTION 'Pulang di luar radius toleransi (% m > % m): isi penjelasan.',
              NEW.check_out_distance_m, v_radius USING ERRCODE = '23514';
          END IF;
        END IF;
        IF NEW.status = 'AUTO_VALID' THEN
          NEW.status := 'NEEDS_REVIEW';
        END IF;
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER attendance_checkout BEFORE UPDATE ON attendance
  FOR EACH ROW EXECUTE FUNCTION tg_attendance_checkout();

-- -----------------------------------------------------------------------------
-- Cakupan absensi R-33 (Alembic 0015): siapa melihat & siapa meninjau — satu sumber aturan.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION attendance_pm_subordinate(p_viewer uuid, p_employee uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM vms.employee te
    JOIN vms.user_role pr ON pr.user_id = p_viewer AND pr.role = 'PM'
    WHERE te.id = p_employee AND te.attendance_mode = 'FIELD'
      AND pr.unit_id IS NOT NULL AND pr.unit_id = te.unit_id)
$$;

CREATE OR REPLACE FUNCTION attendance_is_finance(p_employee uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM vms.app_user tu JOIN vms.user_role tr ON tr.user_id = tu.id
    WHERE tu.employee_id = p_employee AND tr.role = 'FINANCE')
$$;

CREATE OR REPLACE FUNCTION attendance_viewable(p_viewer uuid, p_view_all boolean, p_employee uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT p_view_all
      OR p_employee = (SELECT employee_id FROM vms.app_user WHERE id = p_viewer)
      OR vms.attendance_pm_subordinate(p_viewer, p_employee)
$$;

CREATE OR REPLACE FUNCTION attendance_can_review(p_viewer uuid, p_employee uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT p_employee IS DISTINCT FROM (SELECT employee_id FROM vms.app_user WHERE id = p_viewer)
     AND (vms.attendance_pm_subordinate(p_viewer, p_employee)
          OR (EXISTS (SELECT 1 FROM vms.user_role r WHERE r.user_id = p_viewer AND r.role = 'FINANCE')
              AND EXISTS (SELECT 1 FROM vms.employee te WHERE te.id = p_employee AND te.attendance_mode = 'OFFICE')
              AND NOT vms.attendance_is_finance(p_employee))
          OR (EXISTS (SELECT 1 FROM vms.user_role r WHERE r.user_id = p_viewer AND r.role = 'OPS')
              AND vms.attendance_is_finance(p_employee)))
$$;

-- -----------------------------------------------------------------------------
-- Bentrok jadwal personel: satu orang tidak boleh berada di dua pekerjaan aktif
-- yang periodenya beririsan. Dipakai UI (untuk menandai) dan trigger (untuk menolak).
-- -----------------------------------------------------------------------------
-- Per HARI BERTUGAS (Alembic 0033): bentrok hanya bila ada tanggal yang sama di mana ia bertugas di dua rencana.
CREATE OR REPLACE FUNCTION vms.personnel_conflict(p_employee uuid, p_period daterange, p_exclude_plan uuid DEFAULT NULL)
RETURNS TABLE (work_plan_id uuid, number text, title text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = vms, public AS $$
  SELECT DISTINCT wp.id, wp.number, wp.title
  FROM vms.work_plan wp
  JOIN vms.work_plan_member m ON m.work_plan_id = wp.id AND upper_inf(m.valid_period)
  JOIN vms.work_plan_day d ON d.work_plan_id = wp.id
  WHERE m.employee_id = p_employee
    AND wp.deleted_at IS NULL
    AND wp.status IN ('PUBLISHED','ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW')
    AND (p_exclude_plan IS NULL OR wp.id <> p_exclude_plan)
    AND p_period @> d.work_date
    AND 
    (NOT EXISTS (SELECT 1 FROM vms.work_plan_day_member dm WHERE dm.work_plan_day_id = d.id)
     OR EXISTS (SELECT 1 FROM vms.work_plan_day_member dm
                WHERE dm.work_plan_day_id = d.id AND dm.employee_id = p_employee))

    AND (p_exclude_plan IS NULL
         OR NOT EXISTS (SELECT 1 FROM vms.work_plan_day c WHERE c.work_plan_id = p_exclude_plan)
         OR EXISTS (SELECT 1 FROM vms.work_plan_day c
                    WHERE c.work_plan_id = p_exclude_plan AND c.work_date = d.work_date
                      AND 
    (NOT EXISTS (SELECT 1 FROM vms.work_plan_day_member dm WHERE dm.work_plan_day_id = c.id)
     OR EXISTS (SELECT 1 FROM vms.work_plan_day_member dm
                WHERE dm.work_plan_day_id = c.id AND dm.employee_id = p_employee))
))
$$;

-- Tanggal (hari ini dan sesudahnya) di mana karyawan bertugas pada rencana aktif lain (Alembic 0033).
CREATE OR REPLACE FUNCTION vms.employee_busy_dates(p_employee uuid, p_exclude_plan uuid DEFAULT NULL)
RETURNS TABLE (busy_date date)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = vms, public AS $$
  SELECT DISTINCT d.work_date
  FROM vms.work_plan wp
  JOIN vms.work_plan_member m ON m.work_plan_id = wp.id AND upper_inf(m.valid_period)
  JOIN vms.work_plan_day d ON d.work_plan_id = wp.id
  JOIN vms.organization o ON o.id = wp.organization_id
  WHERE m.employee_id = p_employee
    AND wp.deleted_at IS NULL
    AND wp.status IN ('PUBLISHED','ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW')
    AND (p_exclude_plan IS NULL OR wp.id <> p_exclude_plan)
    AND d.work_date >= (now() AT TIME ZONE o.timezone)::date
    AND 
    (NOT EXISTS (SELECT 1 FROM vms.work_plan_day_member dm WHERE dm.work_plan_day_id = d.id)
     OR EXISTS (SELECT 1 FROM vms.work_plan_day_member dm
                WHERE dm.work_plan_day_id = d.id AND dm.employee_id = p_employee))

  ORDER BY d.work_date
$$;

-- Alur SK v2 (Alembic 0018): "tidak terikat SK" = bukan ketua/anggota/driver SK aktif mana pun,
-- tanpa melihat tanggal. Dipakai pilihan form "Buat SK" dan validasi simpan.
CREATE OR REPLACE FUNCTION employee_is_bound(p_employee uuid, p_exclude_plan uuid DEFAULT NULL)
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM work_plan wp
    WHERE wp.deleted_at IS NULL
      AND wp.status IN ('PUBLISHED','APPEALED','ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW')
      AND (p_exclude_plan IS NULL OR wp.id <> p_exclude_plan)
      AND (EXISTS (SELECT 1 FROM work_plan_member m
                   WHERE m.work_plan_id = wp.id AND m.employee_id = p_employee AND upper_inf(m.valid_period))
           OR EXISTS (SELECT 1 FROM asset_allocation al
                      WHERE al.work_plan_id = wp.id AND al.driver_employee_id = p_employee
                        AND al.released_at IS NULL))
  )
$$;

CREATE OR REPLACE FUNCTION tg_member_no_conflict() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE v_period daterange; v_conflict record;
BEGIN
  SELECT period INTO v_period FROM work_plan WHERE id = NEW.work_plan_id;
  SELECT * INTO v_conflict FROM personnel_conflict(NEW.employee_id, v_period, NEW.work_plan_id) LIMIT 1;
  IF FOUND THEN
    RAISE EXCEPTION 'Jadwal personel bertabrakan dengan %.', COALESCE(v_conflict.number, v_conflict.title)
      USING ERRCODE = '23505';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER work_plan_member_conflict BEFORE INSERT ON work_plan_member
  FOR EACH ROW EXECUTE FUNCTION tg_member_no_conflict();

-- Kendaraan hanya boleh dialokasikan bila pengemudi punya SIM yang masih berlaku
-- sampai tanggal selesai pekerjaan.
CREATE OR REPLACE FUNCTION tg_vehicle_driver_licence() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  v_kind asset_kind; v_vehicle text; v_needed text; v_end date; v_expiry date;
BEGIN
  SELECT kind, vehicle_type INTO v_kind, v_vehicle FROM asset WHERE id = NEW.asset_id;
  IF v_kind <> 'VEHICLE' THEN RETURN NEW; END IF;

  IF NEW.driver_employee_id IS NULL THEN
    RAISE EXCEPTION 'Pilih pengemudi untuk aset kendaraan.' USING ERRCODE = '23514';
  END IF;

  SELECT upper(period) - 1 INTO v_end FROM work_plan WHERE id = NEW.work_plan_id;
  v_needed := CASE WHEN v_vehicle = 'MOTORCYCLE' THEN 'SIM C' ELSE 'SIM A' END;

  SELECT expiry_date INTO v_expiry
  FROM employee_document
  WHERE employee_id = NEW.driver_employee_id AND doc_type = v_needed AND lifecycle = 'CURRENT';

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Pengemudi tidak memiliki % aktif dalam profilnya.', v_needed USING ERRCODE = '23514';
  END IF;
  IF v_expiry IS NOT NULL AND v_expiry < v_end THEN
    RAISE EXCEPTION 'Masa berlaku % pengemudi kedaluwarsa sebelum jadwal selesai.', v_needed USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER asset_allocation_driver BEFORE INSERT ON asset_allocation
  FOR EACH ROW EXECUTE FUNCTION tg_vehicle_driver_licence();

-- -----------------------------------------------------------------------------
-- QR: terbitkan dan verifikasi. Token mentah hanya ada di dalam kode QR.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION issue_qr_token(
  p_org uuid, p_purpose qr_purpose, p_subject_type text, p_subject_id uuid,
  p_issued_by uuid, p_expires_at timestamptz DEFAULT NULL,
  p_max_scans integer DEFAULT NULL, p_site uuid DEFAULT NULL, p_radius integer DEFAULT NULL
) RETURNS TABLE (token_id uuid, raw_token text)
LANGUAGE plpgsql AS $$
DECLARE v_raw text; v_id uuid;
BEGIN
  v_raw := encode(gen_random_bytes(32), 'base64');   -- dikirim sekali, lalu dilupakan basis data
  INSERT INTO qr_token (organization_id, purpose, subject_type, subject_id, token_sha256,
                        site_id, allowed_radius_m, issued_by, expires_at, max_scans)
  VALUES (p_org, p_purpose, p_subject_type, p_subject_id, digest(v_raw, 'sha256'),
          p_site, p_radius, p_issued_by, p_expires_at, p_max_scans)
  RETURNING id INTO v_id;
  RETURN QUERY SELECT v_id, v_raw;
END $$;

CREATE OR REPLACE FUNCTION verify_qr_scan(
  p_raw_token text, p_purpose qr_purpose, p_scanned_by uuid,
  p_location geography DEFAULT NULL, p_image_file uuid DEFAULT NULL,
  p_device text DEFAULT NULL
) RETURNS TABLE (result qr_scan_result, subject_type text, subject_id uuid)
LANGUAGE plpgsql AS $$
DECLARE
  v_token qr_token%ROWTYPE;
  v_result qr_scan_result;
  v_distance numeric(8,1);
  v_radius integer;
BEGIN
  SELECT * INTO v_token FROM qr_token WHERE token_sha256 = digest(p_raw_token, 'sha256');

  IF NOT FOUND THEN
    v_result := 'UNKNOWN_TOKEN';
  ELSIF v_token.purpose <> p_purpose THEN
    v_result := 'WRONG_PURPOSE';
  ELSIF v_token.revoked_at IS NOT NULL THEN
    v_result := 'REVOKED';
  ELSIF v_token.expires_at IS NOT NULL AND v_token.expires_at < now() THEN
    v_result := 'EXPIRED';
  ELSIF v_token.max_scans IS NOT NULL AND v_token.scan_count >= v_token.max_scans THEN
    v_result := 'LIMIT_REACHED';
  ELSE
    v_result := 'VALID';
    IF v_token.site_id IS NOT NULL AND p_location IS NOT NULL THEN
      SELECT round(ST_Distance(p_location, s.location)::numeric, 1), COALESCE(v_token.allowed_radius_m, s.radius_m, 100)
        INTO v_distance, v_radius
      FROM site s WHERE s.id = v_token.site_id;
      IF v_distance > v_radius THEN v_result := 'OUT_OF_RANGE'; END IF;
    END IF;
  END IF;

  INSERT INTO qr_scan (qr_token_id, scanned_by, result, location, distance_m, device_label, image_file_id)
  VALUES (v_token.id, p_scanned_by, v_result, p_location, v_distance, p_device, p_image_file);

  IF v_result = 'VALID' THEN
    UPDATE qr_token SET scan_count = scan_count + 1 WHERE id = v_token.id;
  END IF;

  RETURN QUERY SELECT v_result, v_token.subject_type, v_token.subject_id;
END $$;

-- -----------------------------------------------------------------------------
-- Sinkronisasi luring: idempoten. Pengiriman ulang op yang sama tidak menggandakan.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enqueue_offline_operation(
  p_org uuid, p_user uuid, p_device text, p_client_op uuid,
  p_type text, p_payload jsonb, p_client_created timestamptz
) RETURNS uuid
LANGUAGE plpgsql AS $$
DECLARE v_id uuid;
BEGIN
  INSERT INTO offline_operation (organization_id, user_id, device_id, client_op_id, op_type, payload, client_created_at)
  VALUES (p_org, p_user, p_device, p_client_op, p_type, p_payload, p_client_created)
  ON CONFLICT (user_id, client_op_id) DO UPDATE SET received_at = now()
  RETURNING id INTO v_id;
  RETURN v_id;
END $$;

-- -----------------------------------------------------------------------------
-- Tampilan siap pakai untuk layar rekap
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_overtime_recap AS
SELECT o.organization_id,
       date_trunc('month', o.work_date)::date AS period_month,
       o.employee_id,
       e.full_name,
       count(*) FILTER (WHERE o.status = 'APPROVED')    AS approved_entries,
       count(*) FILTER (WHERE o.status = 'PENDING_PM')  AS pending_entries,
       COALESCE(sum(o.hours) FILTER (WHERE o.status = 'APPROVED'), 0) AS approved_hours
FROM overtime_log o
JOIN employee e ON e.id = o.employee_id
GROUP BY o.organization_id, period_month, o.employee_id, e.full_name;

CREATE OR REPLACE VIEW v_document_expiry AS
-- "Hari ini" menurut zona waktu organisasi (K-11), bukan CURRENT_DATE server DB (UTC) — dulu
-- dokumen yang kedaluwarsa kemarin masih "kurang dari 7 hari" antara 00.00–07.00 WIB (R-18).
SELECT d.id, e.organization_id, e.id AS employee_id, e.full_name, d.doc_type, d.expiry_date,
       (d.expiry_date - t.today) AS days_left,
       CASE WHEN d.expiry_date < t.today THEN 'KEDALUWARSA'
            WHEN d.expiry_date <= t.today + 7 THEN 'KURANG_DARI_7_HARI'
            WHEN d.expiry_date <= t.today + 30 THEN 'KURANG_DARI_30_HARI'
            ELSE 'AMAN' END AS urgency
FROM employee_document d
JOIN employee e ON e.id = d.employee_id
JOIN organization o ON o.id = e.organization_id
CROSS JOIN LATERAL (SELECT (now() AT TIME ZONE o.timezone)::date AS today) t
WHERE d.lifecycle = 'CURRENT' AND d.expiry_date IS NOT NULL AND e.deleted_at IS NULL;

CREATE OR REPLACE VIEW v_plan_progress AS
SELECT wp.id AS work_plan_id, wp.organization_id, wp.unit_id, wp.title, wp.status, wp.period,
       count(d.id) AS total_days,
       count(*) FILTER (WHERE r.status = 'APPROVED') AS approved_days,
       count(*) FILTER (WHERE r.status = 'SUBMITTED') AS waiting_review,
       count(*) FILTER (WHERE lower(wp.period) <= t.today AND d.work_date < t.today
                              AND (r.status IS NULL OR r.status <> 'APPROVED')) AS late_days
FROM work_plan wp
JOIN organization o ON o.id = wp.organization_id
CROSS JOIN LATERAL (SELECT (now() AT TIME ZONE o.timezone)::date AS today) t
LEFT JOIN work_plan_day d ON d.work_plan_id = wp.id
LEFT JOIN daily_report r ON r.work_plan_day_id = d.id
WHERE wp.deleted_at IS NULL
GROUP BY wp.id, t.today;

-- Pembuatan partisi bulan berikutnya; jadwalkan lewat pg_cron atau tugas harian.
CREATE OR REPLACE FUNCTION ensure_month_partitions(p_months integer DEFAULT 3) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE i integer; v_start date; v_end date;
BEGIN
  FOR i IN 0..p_months LOOP
    v_start := date_trunc('month', CURRENT_DATE + (i || ' month')::interval)::date;
    v_end := (v_start + interval '1 month')::date;
    EXECUTE format('CREATE TABLE IF NOT EXISTS attendance_%s PARTITION OF attendance FOR VALUES FROM (%L) TO (%L)',
                   to_char(v_start, 'YYYY"m"MM'), v_start, v_end);
    EXECUTE format('CREATE TABLE IF NOT EXISTS audit_event_%s PARTITION OF audit_event FOR VALUES FROM (%L) TO (%L)',
                   to_char(v_start, 'YYYY"m"MM'), v_start, v_end);
    EXECUTE format('CREATE TABLE IF NOT EXISTS qr_scan_%s PARTITION OF qr_scan FOR VALUES FROM (%L) TO (%L)',
                   to_char(v_start, 'YYYY"m"MM'), v_start, v_end);
  END LOOP;
END $$;

-- Kategori dalam/luar kota dihitung saat dibaca (Alembic 0028_attendance_checkout_city).
CREATE OR REPLACE FUNCTION attendance_city_category(p_employee uuid, p_date date) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = vms, public AS $$
  SELECT CASE WHEN EXISTS (
    SELECT 1
    FROM work_plan wp
    JOIN work_plan_member m ON m.work_plan_id = wp.id AND m.employee_id = p_employee
    WHERE wp.organization_id = current_org_id()
      AND wp.is_out_of_town
      AND wp.status IN ('ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW','COMPLETED')
      AND wp.period @> p_date
      AND m.valid_period @> p_date
  ) THEN 'LUAR_KOTA' ELSE 'DALAM_KOTA' END
$$;
