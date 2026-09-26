"""
Daftar dokumen kedaluwarsa `GET /documents/expiring` (izin verify:documents — HR) dan regresi R2
untuk insiden: PM unit lain tidak melihat insiden SK unit lain. Sebelumnya rute ini belum diuji.
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_in_progress

pytestmark = requires_db


def _document(world: World, days_from_today: int, doc_type: str = "SIM A") -> str:
    expiry = jakarta_now().date() + timedelta(days=days_from_today)
    return str(sync_query(
        "WITH _ctx AS (SELECT set_config('app.organization_id', %s, true)) "
        "INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, expiry_date, status, lifecycle, "
        "uploaded_by) SELECT e.id, %s, '****1234', %s, 'VERIFIED', 'CURRENT', u.id "
        "FROM vms.employee e JOIN vms.app_user u ON u.employee_id = e.id, _ctx WHERE e.id = %s RETURNING id",
        (world.org_id, doc_type, expiry, world.employees["member"]))[0][0])


def _expiring(client, world: World, who: str, **params: str):
    return client.get("/documents/expiring", headers=world.headers(client, who), params=params)


def test_hr_sees_expiring_documents_of_own_organisation_sorted_by_urgency(client, world, other_world):
    # Satu dokumen CURRENT per (karyawan, jenis) — jenisnya dibedakan.
    expired, soon, month, safe = (_document(world, d, t) for d, t in
                                  ((-3, "SIM A"), (5, "SIM C"), (20, "MCU"), (200, "KTP")))
    foreign = _document(other_world, -3)

    response = _expiring(client, world, "hr")
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    ids = [i["id"] for i in items]
    assert foreign not in ids                                        # V-09: organisasi lain tak terlihat
    assert ids.index(expired) < ids.index(soon) < ids.index(month) < ids.index(safe)   # paling mendesak dulu
    urgency = {i["id"]: i["urgency"] for i in items}
    assert (urgency[expired], urgency[soon], urgency[month], urgency[safe]) == \
        ("KEDALUWARSA", "KURANG_DARI_7_HARI", "KURANG_DARI_30_HARI", "AMAN")
    assert {i["full_name"] for i in items} == {"Karyawan uji member"}


def test_expiring_filter_by_urgency(client, world):
    expired, soon = _document(world, -1, "SIM A"), _document(world, 3, "MCU")
    only_expired = _expiring(client, world, "hr", urgency="KEDALUWARSA").json()["items"]
    assert [i["id"] for i in only_expired] == [expired]
    assert soon not in [i["id"] for i in only_expired]


def test_expiring_list_needs_verify_documents_permission(client, world):
    _document(world, -1)
    for who in ("member", "leader", "pm", "finance"):
        assert _expiring(client, world, who).status_code == 403, who


def test_r2_pm_of_another_unit_cannot_list_incidents(client, world):
    """R2 (dok 07 §3): insiden SK unit A tidak bocor ke PM unit B — 404, bukan daftar kosong."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    reported = client.post("/hse/incidents", headers=world.headers(client, "member"), json={
        "work_plan_id": plan_id, "category": "K3_HAMPIR", "severity": "RENDAH",
        "description": "Tangga licin di area gudang."})
    assert reported.status_code == 201, reported.text

    world.add_person("pm_walld", "PM", world.add_unit("WALLD"), per_unit=True)
    assert client.get("/hse/incidents", params={"plan_id": plan_id},
                      headers=world.headers(client, "pm_walld")).status_code == 404
    own = client.get("/hse/incidents", params={"plan_id": plan_id}, headers=world.headers(client, "pm"))
    assert [i["id"] for i in own.json()] == [reported.json()["id"]]


def test_unknown_incident_category_is_422_not_500(client, world):
    """Temuan audit R-18: kategori/tingkat di luar enum DB dulu lolos skema lalu meledak 500 di DB."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    response = client.post("/hse/incidents", headers=world.headers(client, "member"), json={
        "work_plan_id": plan_id, "category": "NEAR_MISS", "severity": "LOW", "description": "Uji nilai salah."})
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
