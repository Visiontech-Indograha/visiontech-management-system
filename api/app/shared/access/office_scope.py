"""
Cakupan kantor untuk data absensi (keputusan pemilik 2026-11-05).

Pemegang `view:all_attendance` tidak otomatis melihat semua kantor:
- SUPER_ADMIN dan OPERATIONAL_MANAGER (peran sistem, atau penjabat OM sebuah divisi `division.om_id`)
  melihat SEMUA kantor;
- peran lain (ADMIN_HR_GA, FINANCE) hanya kantor tempat karyawannya terdaftar (`employee.office_id`).

Cakupan adalah gabungan (union) semua jabatan orang itu: HR kantor A yang juga OM divisi melihat semua kantor.
Akun hanya punya satu `system_role` dan satu `employee.office_id`; jabatan kedua dimodelkan lewat
`division.om_id`. Dihitung di SQL (satu sumber untuk daftar, rekap, ekspor, uang makan, dan akses swafoto).
"""

from __future__ import annotations


def attendance_office_scope(viewer_emp: str, emp_office: str) -> str:
    """Ekspresi boolean SQL: peninjau (`viewer_emp` = ekspresi employee_id) boleh melihat absensi karyawan yang
    kantornya `emp_office` (ekspresi office_id). Kedua argumen adalah ekspresi SQL internal, bukan input pengguna."""
    return f"""(
        EXISTS (SELECT 1 FROM users os WHERE os.employee_id = {viewer_emp} AND os.delete_at IS NULL
                AND os.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER'))
        OR EXISTS (SELECT 1 FROM division od WHERE od.om_id = {viewer_emp} AND od.delete_at IS NULL)
        OR {emp_office} = (SELECT ov.office_id FROM employee ov WHERE ov.employee_id = {viewer_emp})
    )"""
