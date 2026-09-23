"""
Penghapusan organisasi uji beserta seluruh barisnya.

Beberapa FK tidak cascade (mis. `employee_assignment.unit_id`, `asset_allocation.allocated_by`,
`daily_report.submitted_by`), dan `tg_audit_row()` butuh konteks `app.organization_id` untuk tabel
tanpa kolom organisasi (`asset_allocation`). Karena itu: satu koneksi, konteks disetel, dan baris
penahan dihapus berulang sampai organisasinya bisa dihapus.
"""
from __future__ import annotations

import re

import psycopg2

# kolom rujukan → subkueri id milik organisasi %(org)s
_OWNED_IDS = {
    "user_id": "SELECT id FROM vms.app_user WHERE organization_id = %(org)s",
    "employee_id": "SELECT id FROM vms.employee WHERE organization_id = %(org)s",
    "work_plan_id": "SELECT id FROM vms.work_plan WHERE organization_id = %(org)s",
    "asset_id": "SELECT id FROM vms.asset WHERE organization_id = %(org)s",
    "work_plan_day_id": "SELECT d.id FROM vms.work_plan_day d JOIN vms.work_plan w ON w.id = d.work_plan_id "
                        "WHERE w.organization_id = %(org)s",
    "asset_allocation_id": "SELECT a.id FROM vms.asset_allocation a JOIN vms.asset s ON s.id = a.asset_id "
                           "WHERE s.organization_id = %(org)s",
    "daily_report_id": "SELECT r.id FROM vms.daily_report r JOIN vms.work_plan_day d ON d.id = r.work_plan_day_id "
                       "JOIN vms.work_plan w ON w.id = d.work_plan_id WHERE w.organization_id = %(org)s",
}
_BLOCKER = re.compile(r'on table "(\w+)"\s*DETAIL')


def purge_organization(conn: psycopg2.extensions.connection, org_id: str, max_rounds: int = 40) -> None:
    for _ in range(max_rounds):
        cur = conn.cursor()
        try:
            cur.execute("SELECT set_config('app.organization_id', %s, true), "
                        "set_config('app.actor_label', 'pembersihan-uji', true)", (org_id,))
            cur.execute("DELETE FROM vms.attendance WHERE organization_id = %s", (org_id,))
            cur.execute("DELETE FROM vms.organization WHERE id = %s", (org_id,))
            conn.commit()
            return
        except psycopg2.errors.ForeignKeyViolation as exc:
            conn.rollback()
            match = _BLOCKER.search(str(exc))
            if not match:
                raise
            blocker = match.group(1)
            cur = conn.cursor()
            cur.execute("SELECT set_config('app.organization_id', %s, true)", (org_id,))
            cur.execute("SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'vms' AND table_name = %s", (blocker,))
            columns = {c for (c,) in cur.fetchall()}
            if "organization_id" in columns:
                cur.execute(f"DELETE FROM vms.{blocker} WHERE organization_id = %s", (org_id,))
            else:
                ref = next((c for c in _OWNED_IDS if c in columns), None)
                if ref is None:
                    raise RuntimeError(f"Tidak tahu cara menghapus penahan {blocker} (kolom: {sorted(columns)})") from exc
                cur.execute(f"DELETE FROM vms.{blocker} WHERE {ref} IN ({_OWNED_IDS[ref]})", {"org": org_id})
            conn.commit()
    raise RuntimeError(f"Organisasi uji {org_id} tidak dapat dihapus setelah {max_rounds} putaran")
