"""
Pemantauan kedaluwarsa dokumen karyawan (`GET /documents/expiring`, izin manage:employee_documents) dan
pekerjaan berkala `POST /documents/cron/expire-documents` (dokumen lewat tanggal → not_active).
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _document(world: World, days_from_today: int, doc_type: str) -> str:
    expiry = jakarta_now().date() + timedelta(days=days_from_today)
    return str(sync_query(
        "INSERT INTO employee_file (employee_id, type, path_file, status, active_at, expired_at) "
        "VALUES (%s, %s, %s, 'active', now() - interval '1 year', "
        "%s::date::timestamp AT TIME ZONE 'Asia/Jakarta') RETURNING employee_file_id",
        (world.employees["member"], doc_type, f"uji/{world.tag}/{doc_type}.pdf", expiry))[0][0])


def test_expiring_documents_sorted_by_urgency(client, world: World):
    expired, soon, month, safe = (_document(world, d, t) for d, t in
                                  ((-3, "SIM_A"), (5, "SIM_C"), (20, "MCU"), (200, "KTP")))
    response = client.get("/documents/expiring", headers=world.headers(client, "hr"))
    assert response.status_code == 200, response.text
    mine = [i for i in response.json()["items"] if i["employee_id"] == world.employees["member"]]
    assert [(i["id"], i["urgency"]) for i in mine] == [(expired, "EXPIRED"), (soon, "CRITICAL"), (month, "WARNING")]
    assert safe not in [i["id"] for i in mine]

    critical = client.get("/documents/expiring", headers=world.headers(client, "hr"), params={"urgency": "CRITICAL"})
    assert {i["urgency"] for i in critical.json()["items"]} == {"CRITICAL"}


def test_expiring_list_is_for_document_managers_only(client, world: World):
    assert client.get("/documents/expiring", headers=world.headers(client, "pm")).status_code == 403


def test_cron_deactivates_overdue_documents(client, world: World):
    overdue, today = _document(world, -1, "SIM_A"), _document(world, 0, "SIM_C")
    response = client.post("/documents/cron/expire-documents", headers=world.headers(client, "admin"))
    assert response.status_code == 200, response.text
    status = dict(sync_query("SELECT employee_file_id::text, status::text FROM employee_file "
                             "WHERE employee_file_id IN (%s, %s)", (overdue, today)))
    assert status == {overdue: "not_active", today: "active"}
