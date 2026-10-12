"""Peran runtime API `vms_api` yang tunduk RLS (P9-2, keputusan pemilik 2026-10-08).

Revision ID: 0024_runtime_role
Revises: 0023_face_verify_fix
Create Date: 2026-10-08

Temuan: di produksi API tersambung sebagai `vms_app`, yang sekaligus superuser dan pemilik semua tabel (dibuat
oleh `POSTGRES_USER` citra Docker). Superuser dan pemilik tabel melewati RLS, jadi 20 kebijakan di db/03–05 tidak
pernah berlaku. Revisi ini membuat peran terpisah untuk koneksi aplikasi: bukan superuser, bukan pemilik, tanpa
BYPASSRLS. Sandinya TIDAK diatur di sini — pemilik menyetelnya di server (deploy/README.md).

Batas RLS = tenant (organisasi); pembatasan per unit/keterlibatan tetap di service. Fungsi basis data berjalan
sebagai pemilik (SECURITY DEFINER) agar aturan lintas data (bentrok personel, SIM, verifikasi QR) tetap utuh.

Hak akses = yang dipakai aplikasi: baca/tulis/ubah semua tabel, hapus hanya pada tabel yang memang dihapus kode
(lampiran & detail draf, bukti laporan, ketua SK, sesi), tidak pernah mengubah/menghapus audit, dan TIDAK punya akses
langsung ke partisi (`attendance_*`, `audit_event_*`, `qr_scan_*`) — RLS hanya terpasang di tabel induk.
Tidak ada default privileges: partisi baru dari `ensure_partitions()` otomatis tanpa akses; tabel baru di migrasi
berikutnya wajib GRANT ke vms_api (dijaga `tests/test_rls_app_role.py`).

Migrasi tetap memakai peran pemilik (`MIGRATION_DATABASE_URL`, bila kosong `DATABASE_URL`).
Isi SQL sama dengan bagian akhir `db/05_face.sql`.
"""
import re
from collections.abc import Iterator, Sequence

from alembic import op

revision: str = "0024_runtime_role"
down_revision: str | None = "0023_face_verify_fix"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUNTIME_ROLE_SQL = """
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
"""


def _statements(sql: str) -> Iterator[str]:
    """Pecah per perintah (asyncpg menolak beberapa perintah dalam satu op.execute); `;` di dalam $..$ diabaikan."""
    buf: list[str] = []
    quoted = False
    for line in sql.splitlines():
        if not buf and (not line.strip() or line.lstrip().startswith("--")):
            continue
        buf.append(line)
        quoted ^= len(re.findall(r"\$[a-z]*\$", line)) % 2 == 1
        if not quoted and line.rstrip().endswith(";"):
            yield "\n".join(buf)
            buf = []
    assert not buf, "SQL 0024 berakhir di tengah perintah"


def upgrade() -> None:
    for stmt in _statements(RUNTIME_ROLE_SQL):
        op.execute(stmt)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
            REVOKE ALL ON ALL TABLES IN SCHEMA vms FROM vms_api;
            REVOKE ALL ON ALL SEQUENCES IN SCHEMA vms FROM vms_api;
            REVOKE ALL ON ALL FUNCTIONS IN SCHEMA vms FROM vms_api;
            REVOKE USAGE ON SCHEMA vms FROM vms_api;
            BEGIN
              DROP ROLE vms_api;
            EXCEPTION WHEN dependent_objects_still_exist THEN
              -- Peran berlaku untuk seluruh klaster; masih punya hak di basis data lain → biarkan, tanpa hak di sini.
              RAISE NOTICE 'vms_api tidak dihapus: masih dipakai di basis data lain';
            END;
          END IF;
        END $$
    """)
    # Kebijakan yang dilonggarkan ke batas tenant & SECURITY DEFINER dibiarkan: peran pemilik melewati RLS,
    # jadi perilakunya sama dengan sebelum 0024.
    op.execute("DROP FUNCTION IF EXISTS vms.employees_with_valid_licence(uuid[], text, date)")
