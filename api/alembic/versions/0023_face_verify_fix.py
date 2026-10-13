"""Perbaiki verify_face_for_attendance: galat "record v_self is not assigned yet" pada hasil SKIPPED/NOT_ENROLLED/LOW_QUALITY.

Revision ID: 0023_face_verify_fix
Revises: 0022_face_attendance
Create Date: 2026-10-06

Pada tiga jalur itu `v_self` (record) tidak pernah diisi, tetapi tetap dibaca saat mencatat `face_check` sehingga
absen berwajah menjadi 500 alih-alih "Perlu review". Variabel record diganti skalar yang selalu terdefinisi.
Revisi 0022 sudah diterapkan di produksi, jadi perbaikannya revisi baru (revisi yang sudah jalan tidak diubah).
Isi SQL sama dengan `db/05_face.sql`. Ditemukan oleh uji integrasi berbasis DB (`test_face_integration.py`).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0023_face_verify_fix"
down_revision: str | None = "0022_face_attendance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VERIFY_FIXED = """
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
"""


def upgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute(_VERIFY_FIXED)


def downgrade() -> None:
    # Fungsi hanya diperbaiki (tanda tangan & hasil sama). Tidak ada alasan kembali ke versi yang melempar galat.
    pass
