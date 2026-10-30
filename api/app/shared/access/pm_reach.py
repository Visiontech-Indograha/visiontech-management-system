"""
Jangkauan PM atas karyawan (dasar absensi, swafoto, dan peninjauan).

Seorang PM (peran sistem PROJECT_MANAGER) berwenang atas seorang karyawan bila:
- karyawan itu ada di divisi yang dipimpin PM (`division.pm_id`), atau
- karyawan itu ketua/anggota aktif tim pada jadwal harian (`work_plan_daily`) yang PM kelola: divisinya
  dipimpin PM (`division.pm_id`) atau proyeknya dikelola PM (`project.pm_id`).

Dipakai sebagai satu sumber SQL agar daftar, peninjauan, ekspor, dan akses berkas memakai aturan yang sama.
"""

from __future__ import annotations

# Ekspresi SQL yang menghasilkan employee_id peninjau (PM) dari parameter :viewer (user_id).
VIEWER_EMPLOYEE_BY_USER = "(SELECT u.employee_id FROM users u WHERE u.user_id = CAST(:viewer AS uuid))"


def pm_reaches_employee(viewer_emp: str, emp: str) -> str:
    """Ekspresi boolean SQL: `viewer_emp` (employee_id PM) berwenang atas `emp` (employee_id karyawan).

    Kedua argumen adalah ekspresi SQL yang sudah berupa employee_id (bukan teks bebas dari pengguna).
    Bila salah satunya NULL, hasilnya bukan TRUE."""
    return f"""(
        EXISTS (
            SELECT 1 FROM employee rp_e JOIN division rp_d ON rp_d.division_id = rp_e.division_id
            WHERE rp_e.employee_id = {emp} AND rp_d.pm_id = {viewer_emp}
        )
        OR EXISTS (
            SELECT 1 FROM work_plan_daily rp_w
            JOIN division rp_wd ON rp_wd.division_id = rp_w.division_id
            JOIN team rp_t ON rp_t.team_id = rp_w.team_id
            LEFT JOIN project rp_p ON rp_p.project_id = rp_w.project_id AND rp_p.delete_at IS NULL
            WHERE rp_w.delete_at IS NULL
              AND (rp_wd.pm_id = {viewer_emp} OR rp_p.pm_id = {viewer_emp})
              AND (
                  rp_t.leader_employee_id = {emp}
                  OR EXISTS (
                      SELECT 1 FROM member rp_m
                      WHERE rp_m.team_id = rp_w.team_id AND rp_m.employee_id = {emp}
                        AND rp_m.is_active AND rp_m.delete_at IS NULL
                  )
              )
        )
    )"""
