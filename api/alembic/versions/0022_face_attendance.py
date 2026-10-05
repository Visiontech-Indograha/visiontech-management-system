"""Absensi wajah masuk & pulang di HP: gambar wajah sementara (face_probe), hasil wajah saat pulang, fungsi pencocokan.

Revision ID: 0022_face_attendance
Revises: 0021_fk_indexes
Create Date: 2026-10-05

- `face_probe`: gambar wajah sementara + embedding yang dikirim HP saat absen (bukan foto absensi). Dihapus sesuai
  `organization.face_probe_retention_days`. `embedding` NULL = face-service sedang mati; diperiksa ulang kemudian.
- `attendance.check_out_face_*`: hasil pengenalan wajah saat absen pulang (tanpa foto bukti pulang).
- `face_check.attendance_event`: `CHECK_IN`/`CHECK_OUT`.
- `verify_face_for_attendance` menjadi `SECURITY DEFINER`: RLS di `face_enrollment` hanya memperlihatkan baris milik
  sendiri, sehingga pemeriksaan "wajah lebih menyerupai karyawan lain" tidak pernah bekerja dengan hak pengguna biasa.
  `face_best_other_similarity` (juga definer) untuk menolak pendaftaran wajah yang sudah dipakai karyawan lain tanpa
  menyebut siapa. `purge_face_probes` kini juga membersihkan `face_probe`.
- Tabel wajah sudah ada di produksi (`db/05_face.sql`); migrasi ini hanya menambah. Isi SQL sama dengan `db/05_face.sql`.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0022_face_attendance"
down_revision: str | None = "0021_fk_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VERIFY_NEW = """
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
  v_best record;
  v_self record;
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
    SELECT * INTO v_self FROM match_face(p_org, p_embedding, 50) WHERE employee_id = p_claimed_employee LIMIT 1;
    -- kandidat terbaik secara keseluruhan, untuk mendeteksi orang lain yang lebih mirip
    SELECT * INTO v_best FROM match_face(p_org, p_embedding, 1);

    IF v_self.similarity IS NULL OR v_self.similarity < v_org.face_match_threshold THEN
      v_result := 'NO_MATCH';
      v_note := 'Wajah tidak cocok dengan data karyawan tersebut. Absensi ditandai untuk diperiksa.';
    ELSIF v_best.employee_id IS DISTINCT FROM p_claimed_employee THEN
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
  VALUES (p_org, p_claimed_employee, v_self.employee_id, v_self.enrollment_id,
          v_self.similarity, v_org.face_match_threshold, v_result, p_liveness, p_embedding, p_probe_file,
          p_device, p_event)
  RETURNING id INTO v_check;

  RETURN QUERY SELECT v_result, v_self.similarity, v_org.face_match_threshold, v_self.employee_id, v_note, v_check;
END $$;
"""

_VERIFY_OLD = """
CREATE OR REPLACE FUNCTION verify_face_for_attendance(
  p_org uuid,
  p_claimed_employee uuid,
  p_embedding vector(512),
  p_liveness numeric DEFAULT NULL,
  p_probe_file uuid DEFAULT NULL,
  p_device text DEFAULT NULL
) RETURNS TABLE (result face_check_result, similarity numeric, threshold numeric, matched_employee uuid, note text)
LANGUAGE plpgsql AS $$
DECLARE
  v_org organization%ROWTYPE;
  v_best record;
  v_self record;
  v_result face_check_result;
  v_note text;
BEGIN
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
    SELECT * INTO v_self FROM match_face(p_org, p_embedding, 50) WHERE employee_id = p_claimed_employee LIMIT 1;
    SELECT * INTO v_best FROM match_face(p_org, p_embedding, 1);

    IF v_self.similarity IS NULL OR v_self.similarity < v_org.face_match_threshold THEN
      v_result := 'NO_MATCH';
      v_note := 'Wajah tidak cocok dengan data karyawan tersebut. Absensi ditandai untuk diperiksa.';
    ELSIF v_best.employee_id IS DISTINCT FROM p_claimed_employee THEN
      v_result := 'NO_MATCH';
      v_note := 'Wajah lebih menyerupai karyawan lain. Absensi ditandai untuk diperiksa.';
    ELSE
      v_result := 'MATCH';
      v_note := 'Wajah cocok dengan data karyawan.';
    END IF;
  END IF;

  INSERT INTO face_check (organization_id, claimed_employee_id, matched_employee_id, matched_enrollment_id,
                          similarity, threshold_used, result, liveness_score, probe_embedding, probe_file_id, device_label)
  VALUES (p_org, p_claimed_employee, v_self.employee_id, v_self.enrollment_id,
          v_self.similarity, v_org.face_match_threshold, v_result, p_liveness, p_embedding, p_probe_file, p_device);

  RETURN QUERY SELECT v_result, v_self.similarity, v_org.face_match_threshold, v_self.employee_id, v_note;
END $$;
"""

_PURGE_NEW = """
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
"""

_PURGE_OLD = """
CREATE OR REPLACE FUNCTION purge_face_probes() RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_count integer := 0;
BEGIN
  WITH cleaned AS (
    UPDATE face_check fc
       SET probe_embedding = NULL, probe_file_id = NULL
      FROM organization o
     WHERE o.id = fc.organization_id
       AND fc.probe_embedding IS NOT NULL
       AND fc.checked_at < now() - make_interval(days => o.face_probe_retention_days)
    RETURNING 1
  )
  SELECT count(*) INTO v_count FROM cleaned;
  RETURN v_count;
END $$;
"""

_EXPIRED_FILES = """
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
"""

_BEST_OTHER = """
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
"""

_TABLE = """
CREATE TABLE IF NOT EXISTS face_probe (
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
)
"""

_POLICY = """
CREATE POLICY face_probe_visibility ON face_probe
USING (
  organization_id = current_org_id() AND (
    has_role('HR') OR has_role('ADMIN')
    OR employee_id = (SELECT employee_id FROM app_user WHERE id = current_user_id())
  )
)
"""

_GRANTS = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_app') THEN
    GRANT SELECT, INSERT, UPDATE ON vms.face_probe TO vms_app;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_readonly') THEN
    REVOKE ALL ON vms.face_probe FROM vms_readonly;
  END IF;
END $$
"""


def upgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute(_TABLE)
    op.execute("CREATE INDEX IF NOT EXISTS face_probe_employee_idx ON face_probe (employee_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_face_probe_organization_id ON face_probe (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_face_probe_file_id ON face_probe (file_id)")
    op.execute("ALTER TABLE face_probe ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS face_probe_visibility ON face_probe")
    op.execute(_POLICY)
    op.execute(_GRANTS)
    op.execute(
        """
        ALTER TABLE attendance
          ADD COLUMN IF NOT EXISTS check_out_face_check_id uuid,
          ADD COLUMN IF NOT EXISTS check_out_face_result face_check_result,
          ADD COLUMN IF NOT EXISTS check_out_face_similarity numeric(5,4)
        """
    )
    op.execute(
        "ALTER TABLE face_check ADD COLUMN IF NOT EXISTS attendance_event text NOT NULL DEFAULT 'CHECK_IN' "
        "CHECK (attendance_event IN ('CHECK_IN', 'CHECK_OUT'))"
    )
    op.execute("DROP FUNCTION IF EXISTS verify_face_for_attendance(uuid, uuid, vector, numeric, uuid, text)")
    op.execute(_VERIFY_NEW)
    op.execute(_BEST_OTHER)
    op.execute(_PURGE_NEW)
    op.execute(_EXPIRED_FILES)


def downgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute("DROP FUNCTION IF EXISTS expired_face_probe_files()")
    op.execute("DROP FUNCTION IF EXISTS face_best_other_similarity(uuid, uuid, vector)")
    op.execute("DROP FUNCTION IF EXISTS verify_face_for_attendance(uuid, uuid, vector, numeric, uuid, text, text)")
    op.execute(_VERIFY_OLD)
    op.execute(_PURGE_OLD)
    op.execute("ALTER TABLE face_check DROP COLUMN IF EXISTS attendance_event")
    op.execute(
        """
        ALTER TABLE attendance
          DROP COLUMN IF EXISTS check_out_face_similarity,
          DROP COLUMN IF EXISTS check_out_face_result,
          DROP COLUMN IF EXISTS check_out_face_check_id
        """
    )
    op.execute("DROP TABLE IF EXISTS face_probe")
