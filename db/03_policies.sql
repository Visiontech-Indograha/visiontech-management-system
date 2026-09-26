-- =============================================================================
-- Visiontech VMS · Berkas 3 dari 5: peran basis data, hak akses, dan Row Level Security
--
-- Model: aplikasi terhubung sebagai satu peran (vms_app) dan menyetel identitas
-- pengguna per transaksi. Basis data tetap menjadi lapisan penjaga terakhir,
-- sehingga bug pada API tidak langsung membocorkan data lintas unit atau tenant.
-- =============================================================================
SET search_path = vms, public;

-- -----------------------------------------------------------------------------
-- Peran
-- -----------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_app') THEN
    CREATE ROLE vms_app LOGIN;                      -- dipakai API; sandi diatur di luar berkas ini
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_readonly') THEN
    CREATE ROLE vms_readonly LOGIN;                 -- pelaporan / BI
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_migrator') THEN
    CREATE ROLE vms_migrator LOGIN;                 -- hanya untuk migrasi skema
  END IF;
END $$;

GRANT USAGE ON SCHEMA vms TO vms_app, vms_readonly;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA vms TO vms_app;
GRANT SELECT ON ALL TABLES IN SCHEMA vms TO vms_readonly;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA vms TO vms_app;
-- Lampiran draf SK diganti seluruhnya (V-29) → perlu DELETE.
GRANT DELETE ON work_plan_attachment TO vms_app;
-- Penghapusan permanen tidak diberikan: pengarsipan memakai kolom deleted_at.
REVOKE DELETE ON ALL TABLES IN SCHEMA vms FROM vms_app;
-- Audit tidak boleh disunting atau dihapus oleh aplikasi.
REVOKE UPDATE ON audit_event FROM vms_app;

-- Kolom sensitif hanya untuk yang berkepentingan.
REVOKE SELECT ON app_user FROM vms_readonly;
REVOKE ALL ON TABLE app_user FROM PUBLIC;

-- -----------------------------------------------------------------------------
-- Row Level Security
-- Batas pertama: tenant. Batas kedua: unit dan keterlibatan pada pekerjaan.
-- -----------------------------------------------------------------------------
ALTER TABLE organization        ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_unit       ENABLE ROW LEVEL SECURITY;
ALTER TABLE employee            ENABLE ROW LEVEL SECURITY;
ALTER TABLE employee_document   ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_plan           ENABLE ROW LEVEL SECURITY;
ALTER TABLE plan_document       ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance          ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset               ENABLE ROW LEVEL SECURITY;
ALTER TABLE incident_report     ENABLE ROW LEVEL SECURITY;
ALTER TABLE overtime_log        ENABLE ROW LEVEL SECURITY;
ALTER TABLE qr_token            ENABLE ROW LEVEL SECURITY;
ALTER TABLE offline_operation   ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_event         ENABLE ROW LEVEL SECURITY;

-- Tenant: tidak ada baris lintas organisasi yang pernah terlihat.
CREATE POLICY org_isolation ON organization USING (id = current_org_id());
CREATE POLICY unit_isolation ON business_unit USING (organization_id = current_org_id());
CREATE POLICY employee_isolation ON employee USING (organization_id = current_org_id());
CREATE POLICY asset_isolation ON asset USING (organization_id = current_org_id());
CREATE POLICY audit_isolation ON audit_event USING (organization_id = current_org_id());
CREATE POLICY offline_isolation ON offline_operation
  USING (organization_id = current_org_id() AND (user_id = current_user_id() OR has_role('ADMIN')));

-- Work plan: PM/ketua/anggota unitnya sendiri; OPS dan ADMIN lintas unit;
-- pengelola aset hanya melihat pekerjaan yang sudah terbit (bukan draft).
CREATE POLICY work_plan_visibility ON work_plan
USING (
  organization_id = current_org_id() AND (
    has_role('OPS') OR has_role('ADMIN')
    OR (has_role('PM', unit_id))
    OR is_plan_leader(id) OR is_plan_member(id)
    OR (has_role('ASSET') AND status <> 'DRAFT')
  )
);

CREATE POLICY plan_document_visibility ON plan_document
USING (EXISTS (SELECT 1 FROM work_plan wp WHERE wp.id = work_plan_id));  -- mewarisi kebijakan work_plan

-- Absensi: milik sendiri, peran pemeriksa (Finance/HR/OPS), atau PM unit karyawan (R-10).
CREATE POLICY attendance_visibility ON attendance
USING (
  organization_id = current_org_id() AND (
    has_role('FINANCE') OR has_role('HR') OR has_role('OPS') OR has_role('ADMIN')
    OR employee_id = (SELECT employee_id FROM app_user WHERE id = current_user_id())
    -- PM memvalidasi absensi karyawan di unit yang dipegangnya (revisi pemilik R-10)
    OR EXISTS (SELECT 1 FROM employee e
               JOIN user_role ur ON ur.user_id = current_user_id() AND ur.role = 'PM'
               WHERE e.id = attendance.employee_id AND (ur.unit_id IS NULL OR ur.unit_id = e.unit_id))
  )
);

-- Dokumen pribadi: pemilik dan HR saja. PM/OPS tidak boleh melihat berkas pribadi.
CREATE POLICY employee_document_visibility ON employee_document
USING (
  has_role('HR') OR has_role('ADMIN')
  OR employee_id = (SELECT employee_id FROM app_user WHERE id = current_user_id())
);
-- Pengajuan hanya oleh pemiliknya sendiri.
CREATE POLICY employee_document_insert ON employee_document FOR INSERT
WITH CHECK (employee_id = (SELECT employee_id FROM app_user WHERE id = current_user_id()));

-- Insiden dan lembur mengikuti keterlibatan pada pekerjaan.
CREATE POLICY incident_visibility ON incident_report
USING (
  organization_id = current_org_id() AND (
    has_role('OPS') OR has_role('ADMIN') OR (has_role('ASSET') AND category = 'ASET')
    OR EXISTS (SELECT 1 FROM work_plan wp WHERE wp.id = work_plan_id)
  )
);
CREATE POLICY overtime_visibility ON overtime_log
USING (
  organization_id = current_org_id() AND (
    has_role('FINANCE') OR has_role('OPS') OR has_role('ADMIN')
    OR employee_id = (SELECT employee_id FROM app_user WHERE id = current_user_id())
    OR EXISTS (SELECT 1 FROM work_plan wp WHERE wp.id = work_plan_id)
  )
);

-- Token QR: hanya penerbit, peran terkait, dan admin.
CREATE POLICY qr_token_visibility ON qr_token
USING (organization_id = current_org_id() AND (has_role('ADMIN') OR has_role('OPS') OR issued_by = current_user_id()));

-- -----------------------------------------------------------------------------
-- Catatan penerapan
--   1. Aplikasi WAJIB menyetel konteks di awal setiap transaksi:
--        SET LOCAL app.organization_id = '<uuid>';
--        SET LOCAL app.user_id         = '<uuid>';
--        SET LOCAL app.actor_label     = 'Nama Pengguna';
--      Tanpa itu, seluruh kebijakan menghasilkan nol baris (gagal tertutup, bukan terbuka).
--   2. Jangan pernah memakai peran superuser untuk koneksi aplikasi; RLS dilewati olehnya.
--   3. Nomor dokumen pribadi disimpan tersamar (number_masked) beserta hash;
--      nomor aslinya tidak pernah masuk basis data.
--   4. Token QR disimpan sebagai SHA-256. Kode mentah hanya ada pada gambar QR.
-- =============================================================================
