-- Bukti paritas v2_0029 (ADR 0002 fase 1): hanya BACA. Jalankan di DB uji setelah `alembic upgrade head`:
--   psql -d <db_uji> -v ON_ERROR_STOP=1 -f scripts/paritas-penugasan.sql
-- Selisih harus 0 di kedua arah; baris terakhir menampilkan LULUS/GAGAL.
WITH lama AS (
    SELECT u.user_id, u.system_role::text AS role,
           CASE WHEN u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER') THEN NULL
                ELSE e.office_id END AS office_id
    FROM users u LEFT JOIN employee e ON e.employee_id = u.employee_id
    WHERE u.delete_at IS NULL AND u.is_active
      AND u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'ADMIN_HR_GA', 'FINANCE')
      AND (u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER') OR e.office_id IS NOT NULL)
), baru AS (
    SELECT user_id, role::text AS role, office_id
    FROM user_role_assignment WHERE source = 'PRIMARY' AND delete_at IS NULL
), sel AS (
    SELECT 'lama_tanpa_baru' AS arah, count(*) AS n FROM
        (SELECT * FROM lama EXCEPT SELECT * FROM baru) a
    UNION ALL
    SELECT 'baru_tanpa_lama', count(*) FROM
        (SELECT * FROM baru EXCEPT SELECT * FROM lama) b
    UNION ALL
    SELECT 'baris_ganda', count(*) FROM
        (SELECT user_id FROM baru GROUP BY 1 HAVING count(*) > 1) c
    UNION ALL
    SELECT 'indeks_invalid', count(*) FROM pg_index x JOIN pg_class c ON c.oid = x.indexrelid
        WHERE NOT x.indisvalid AND c.relname LIKE 'ix_user_role_assignment%'
)
SELECT arah, n FROM sel
UNION ALL
SELECT CASE WHEN sum(n) = 0 THEN 'LULUS' ELSE 'GAGAL' END, sum(n) FROM sel;
