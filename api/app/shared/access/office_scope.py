"""
Cakupan kantor untuk data absensi (keputusan pemilik 2026-11-05; peran ganda: ADR 0002).

Pemegang `view:all_attendance` tidak otomatis melihat semua kantor:
- SUPER_ADMIN dan OPERATIONAL_MANAGER (peran sistem, atau penjabat OM sebuah divisi `division.om_id`)
  melihat SEMUA kantor;
- peran lain (ADMIN_HR_GA, FINANCE) hanya kantor tempat karyawannya terdaftar (`employee.office_id`).

Cakupan adalah gabungan (union) semua jabatan orang itu: HR kantor A yang juga OM divisi melihat semua kantor.
Dengan `ROLE_ASSIGNMENT_ENABLED` (ADR 0002) jabatan tambahan juga datang dari tabel `user_role_assignment`:
- penugasan OPERATIONAL_MANAGER aktif = semua kantor (OM membawa izin absensi, cakupannya semua kantor);
- penugasan ADMIN_HR_GA / FINANCE = kantor yang ditugaskan saja. Cakupan dihitung per peran pembawa izin:
  izin yang hanya dibawa HR/Finance tidak ikut melebar walau orangnya juga OM (izin absensi dibawa OM,
  sehingga di sini OM menang; izin khusus HR dibatasi di endpoint HR, bukan di cakupan absensi).
Flag mati: ekspresi SQL persis seperti sebelum peran ganda. Dihitung di SQL (satu sumber untuk daftar,
rekap, ekspor, uang makan, dan akses swafoto).
"""

from __future__ import annotations

from app.core.config import settings


def attendance_office_scope(viewer_emp: str, emp_office: str) -> str:
    """Ekspresi boolean SQL: peninjau (`viewer_emp` = ekspresi employee_id) boleh melihat absensi karyawan yang
    kantornya `emp_office` (ekspresi office_id). Kedua argumen adalah ekspresi SQL internal, bukan input pengguna."""
    if not settings.ROLE_ASSIGNMENT_ENABLED:
        return f"""(
        EXISTS (SELECT 1 FROM users os WHERE os.employee_id = {viewer_emp} AND os.delete_at IS NULL
                AND os.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER'))
        OR EXISTS (SELECT 1 FROM division od WHERE od.om_id = {viewer_emp} AND od.delete_at IS NULL)
        OR {emp_office} = (SELECT ov.office_id FROM employee ov WHERE ov.employee_id = {viewer_emp})
    )"""
    return f"""(
        EXISTS (SELECT 1 FROM users os WHERE os.employee_id = {viewer_emp} AND os.delete_at IS NULL
                AND (os.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER')
                     OR EXISTS (SELECT 1 FROM user_role_assignment oa
                                WHERE oa.user_id = os.user_id AND oa.delete_at IS NULL
                                  AND oa.role = 'OPERATIONAL_MANAGER')))
        OR EXISTS (SELECT 1 FROM division od WHERE od.om_id = {viewer_emp} AND od.delete_at IS NULL)
        OR {emp_office} = (SELECT ov.office_id FROM employee ov WHERE ov.employee_id = {viewer_emp})
        OR EXISTS (SELECT 1 FROM users hu
                   JOIN user_role_assignment ha ON ha.user_id = hu.user_id AND ha.delete_at IS NULL
                        AND ha.role IN ('ADMIN_HR_GA', 'FINANCE') AND ha.office_id = {emp_office}
                   JOIN office ho ON ho.office_id = ha.office_id AND ho.delete_at IS NULL
                   WHERE hu.employee_id = {viewer_emp} AND hu.delete_at IS NULL)
    )"""
