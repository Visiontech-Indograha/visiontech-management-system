"""Tanggal "hari ini" pada view kedaluwarsa dokumen & progres SK mengikuti zona waktu organisasi (R-18)

`v_document_expiry` dan `v_plan_progress` memakai CURRENT_DATE server DB (UTC). Antara 00.00–07.00 WIB
dokumen yang kedaluwarsa kemarin masih berstatus "KURANG_DARI_7_HARI" dan `days_left` meleset satu.

Revision ID: 0011_views_org_local_date
Revises: 0010_attendance_pm_unit
Create Date: 2026-09-27
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0011_views_org_local_date"
down_revision: str | Sequence[str] | None = "0010_attendance_pm_unit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = 'CREATE OR REPLACE VIEW vms.v_document_expiry AS\n-- "Hari ini" menurut zona waktu organisasi (K-11), bukan CURRENT_DATE server DB (UTC) — dulu\n-- dokumen yang kedaluwarsa kemarin masih "kurang dari 7 hari" antara 00.00–07.00 WIB (R-18).\nSELECT d.id, e.organization_id, e.id AS employee_id, e.full_name, d.doc_type, d.expiry_date,\n       (d.expiry_date - t.today) AS days_left,\n       CASE WHEN d.expiry_date < t.today THEN \'KEDALUWARSA\'\n            WHEN d.expiry_date <= t.today + 7 THEN \'KURANG_DARI_7_HARI\'\n            WHEN d.expiry_date <= t.today + 30 THEN \'KURANG_DARI_30_HARI\'\n            ELSE \'AMAN\' END AS urgency\nFROM vms.employee_document d\nJOIN vms.employee e ON e.id = d.employee_id\nJOIN vms.organization o ON o.id = e.organization_id\nCROSS JOIN LATERAL (SELECT (now() AT TIME ZONE o.timezone)::date AS today) t\nWHERE d.lifecycle = \'CURRENT\' AND d.expiry_date IS NOT NULL AND e.deleted_at IS NULL;', "CREATE OR REPLACE VIEW vms.v_plan_progress AS\nSELECT wp.id AS work_plan_id, wp.organization_id, wp.unit_id, wp.title, wp.status, wp.period,\n       count(d.id) AS total_days,\n       count(*) FILTER (WHERE r.status = 'APPROVED') AS approved_days,\n       count(*) FILTER (WHERE r.status = 'SUBMITTED') AS waiting_review,\n       count(*) FILTER (WHERE lower(wp.period) <= t.today AND d.work_date < t.today\n                              AND (r.status IS NULL OR r.status <> 'APPROVED')) AS late_days\nFROM vms.work_plan wp\nJOIN vms.organization o ON o.id = wp.organization_id\nCROSS JOIN LATERAL (SELECT (now() AT TIME ZONE o.timezone)::date AS today) t\nLEFT JOIN vms.work_plan_day d ON d.work_plan_id = wp.id\nLEFT JOIN vms.daily_report r ON r.work_plan_day_id = d.id\nWHERE wp.deleted_at IS NULL\nGROUP BY wp.id, t.today;"

_OLD = "CREATE OR REPLACE VIEW vms.v_document_expiry AS\nSELECT d.id, e.organization_id, e.id AS employee_id, e.full_name, d.doc_type, d.expiry_date,\n       (d.expiry_date - CURRENT_DATE) AS days_left,\n       CASE WHEN d.expiry_date < CURRENT_DATE THEN 'KEDALUWARSA'\n            WHEN d.expiry_date <= CURRENT_DATE + 7 THEN 'KURANG_DARI_7_HARI'\n            WHEN d.expiry_date <= CURRENT_DATE + 30 THEN 'KURANG_DARI_30_HARI'\n            ELSE 'AMAN' END AS urgency\nFROM vms.employee_document d\nJOIN vms.employee e ON e.id = d.employee_id\nWHERE d.lifecycle = 'CURRENT' AND d.expiry_date IS NOT NULL AND e.deleted_at IS NULL;\n\nCREATE OR REPLACE VIEW vms.v_plan_progress AS\nSELECT wp.id AS work_plan_id, wp.organization_id, wp.unit_id, wp.title, wp.status, wp.period,\n       count(d.id) AS total_days,\n       count(*) FILTER (WHERE r.status = 'APPROVED') AS approved_days,\n       count(*) FILTER (WHERE r.status = 'SUBMITTED') AS waiting_review,\n       count(*) FILTER (WHERE lower(wp.period) <= CURRENT_DATE AND d.work_date < CURRENT_DATE\n                              AND (r.status IS NULL OR r.status <> 'APPROVED')) AS late_days\nFROM vms.work_plan wp\nLEFT JOIN vms.work_plan_day d ON d.work_plan_id = wp.id\nLEFT JOIN vms.daily_report r ON r.work_plan_day_id = d.id\nWHERE wp.deleted_at IS NULL\nGROUP BY wp.id;"


def upgrade() -> None:
    for sql in _NEW:
        op.execute(sql)


def downgrade() -> None:
    for sql in _OLD.split(";\n\n"):  # satu pernyataan per execute (asyncpg)
        op.execute(sql)
