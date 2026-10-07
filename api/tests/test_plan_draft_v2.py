"""
Form "Buat SK" / "Ubah isi SK" alur v2 (services/plan_draft_service.py, flowchart SK2-A/B).
- POST /work-plans/full: satu simpan = SK + hari & detail pekerjaan + tim + alat + kendaraan/driver → Draf.
- PUT /work-plans/{id}/full: menyusun ulang isi draf (row_version wajib, hanya selama Draf).
- Aturan: setiap tanggal dalam rentang punya 1..30 detail; ketua/anggota staf lapangan bawahan PM yang
  tidak terikat SK lain; alat/kendaraan bebas; driver anggota tim ber-SIM sesuai sampai tanggal selesai.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.test_asset_reservation import _asset, _give_sim_a

pytestmark = requires_db


def _body(world: World, *, days: int = 2, **override: Any) -> dict[str, Any]:
    start = jakarta_now().date() + timedelta(days=1)
    body: dict[str, Any] = {
        "title": "Instalasi CCTV gudang", "description": "Pasang 8 kamera", "category": "INSTALASI",
        "site_id": world.site_id,
        "period_start": start.isoformat(), "period_end": (start + timedelta(days=days - 1)).isoformat(),
        "days": [{"work_date": (start + timedelta(days=i)).isoformat(),
                  "tasks": [{"title": f"Tugas hari {i + 1}", "description": "Rincian"}]} for i in range(days)],
        "leader_employee_id": world.employees["leader"], "member_employee_ids": [world.employees["member"]],
    }
    body.update(override)
    return body


def _create(client, world: World, who: str = "pm", **override: Any):
    return client.post("/work-plans/full", headers=world.headers(client, who), json=_body(world, **override))


def _detail(client, world: World, plan_id: str) -> dict[str, Any]:
    response = client.get(f"/work-plans/{plan_id}/detail", headers=world.headers(client, "pm"))
    assert response.status_code == 200, response.text
    return response.json()


def _row_version(plan_id: str) -> int:
    return int(sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0])


def test_full_create_saves_everything_and_reads_back(client, world):
    _give_sim_a(world, "leader")
    tool = _asset(client, world, "TL-V2")
    car = _asset(client, world, "KD-V2", kind="VEHICLE")

    created = _create(client, world, tool_ids=[tool], vehicle_id=car, driver_employee_id=world.employees["leader"])

    assert created.status_code == 201, created.text
    plan_id = created.json()["plan"]["id"]
    assert sync_query("SELECT status::text, category, unit_id::text FROM vms.work_plan WHERE id = %s", (plan_id,)) \
        == [("DRAFT", "INSTALASI", world.unit_id)]
    detail = _detail(client, world, plan_id)                                     # tulis → baca ulang
    assert detail["plan"]["category_label"] == "Instalasi"
    assert len(detail["days"]) == 2
    assert {m["employee_id"] for m in detail["team"]} == {world.employees["leader"], world.employees["member"]}
    assert {a["asset_id"] for a in detail["assets"]} == {tool, car}
    assert next(a for a in detail["assets"] if a["asset_id"] == car)["driver_employee_id"] == world.employees["leader"]
    assert sync_query("SELECT status::text FROM vms.asset WHERE id IN (%s, %s)", (tool, car)) \
        == [("RESERVED",), ("RESERVED",)]


@pytest.mark.parametrize(("override", "message"), [
    ({"title": "  "}, "Judul pekerjaan wajib diisi."),
    ({"description": ""}, "Deskripsi pekerjaan wajib diisi."),
    ({"site_id": None}, "Pilih lokasi kerja atau tambahkan lokasi baru."),
    ({"site_id": None, "new_site": {"name": " ", "lat": -6.2, "lng": 106.8}}, "Nama lokasi wajib diisi."),
    ({"member_employee_ids": []}, "Pilih minimal satu anggota tim."),
])
def test_full_create_rejects_incomplete_forms(client, world, override, message):
    response = _create(client, world, **override)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["message"] == message


def test_every_date_needs_one_to_thirty_complete_tasks(client, world):
    body = _body(world, days=2)
    missing_day = {**body, "days": body["days"][:1]}
    duplicate = {**body, "days": [body["days"][0], body["days"][0]]}
    for data in (missing_day, duplicate):
        response = client.post("/work-plans/full", headers=world.headers(client, "pm"), json=data)
        assert response.status_code == 422
        assert response.json()["error"]["message"] == "Setiap tanggal dalam rentang work plan wajib punya detail pekerjaan."

    no_tasks = {**body, "days": [{**body["days"][0], "tasks": []}, body["days"][1]]}
    assert "1 sampai 30" in client.post("/work-plans/full", headers=world.headers(client, "pm"),
                                        json=no_tasks).json()["error"]["message"]
    blank = {**body, "days": [{**body["days"][0], "tasks": [{"title": "Ada", "description": " "}]}, body["days"][1]]}
    assert "wajib diisi" in client.post("/work-plans/full", headers=world.headers(client, "pm"),
                                        json=blank).json()["error"]["message"]

    reversed_period = _create(client, world, period_end=(jakarta_now().date()).isoformat())
    assert reversed_period.json()["error"]["message"] == "Tanggal selesai tidak boleh sebelum tanggal mulai."


def test_team_rules(client, world):
    leader, member, hr = (world.employees[w] for w in ("leader", "member", "hr"))

    twice = _create(client, world, member_employee_ids=[leader])
    assert twice.status_code == 422 and twice.json()["error"]["message"] == "Ketua tim tidak boleh dipilih lagi sebagai anggota."
    office = _create(client, world, member_employee_ids=[member, hr])            # akun HR = akun kantor
    assert office.status_code == 422 and office.json()["error"]["code"] == "PERSONNEL_NOT_FIELD_STAFF"

    first = _create(client, world)
    assert first.status_code == 201
    assert _create(client, world).status_code == 201                            # draf tidak mengikat orang
    sync_query("UPDATE vms.work_plan SET status = 'PUBLISHED' WHERE id = %s", (first.json()["plan"]["id"],))
    bound = _create(client, world)                                               # SK pertama terbit → terikat
    assert bound.status_code == 409 and bound.json()["error"]["code"] == "PERSONNEL_BOUND"


def test_asset_and_driver_rules(client, world):
    leader, member = world.employees["leader"], world.employees["member"]
    car = _asset(client, world, "KD-DRV", kind="VEHICLE")

    unknown_tool = _create(client, world, tool_ids=[world.site_id])               # bukan aset bebas
    assert unknown_tool.status_code == 409 and unknown_tool.json()["error"]["code"] == "ASSET_UNAVAILABLE"
    no_driver = _create(client, world, vehicle_id=car)
    assert no_driver.json()["error"]["message"] == "Pilih driver kendaraan."
    outsider = _create(client, world, vehicle_id=car, driver_employee_id=world.employees["hr"])
    assert outsider.json()["error"]["message"] == "Driver harus ketua atau anggota tim yang dipilih."
    unlicensed = _create(client, world, vehicle_id=car, driver_employee_id=member)
    assert unlicensed.status_code == 422 and "SIM A" in unlicensed.json()["error"]["message"]

    _give_sim_a(world, "leader")
    end = (jakarta_now().date() + timedelta(days=2)).isoformat()
    options = client.get("/work-plans/driver-options", headers=world.headers(client, "pm"),
                         params={"vehicle_id": car, "candidate_ids": [leader, member], "period_end": end})
    assert options.status_code == 200, options.text
    assert options.json() == [leader]                                            # hanya yang ber-SIM A
    assert _create(client, world, vehicle_id=car, driver_employee_id=leader).status_code == 201


def test_new_site_belongs_to_the_pm_unit_and_names_are_unique(client, world):
    site = {"name": "Gedung Baru Rumbai", "description": "Lantai 3", "lat": 0.53, "lng": 101.42}
    created = _create(client, world, site_id=None, new_site=site)
    assert created.status_code == 201, created.text
    assert sync_query("SELECT unit_id::text, description FROM vms.site WHERE name = %s AND organization_id = %s",
                      (site["name"], world.org_id)) == [(world.unit_id, "Lantai 3")]

    sync_query("DELETE FROM vms.work_plan_member WHERE work_plan_id = %s", (created.json()["plan"]["id"],))
    duplicate = _create(client, world, site_id=None, new_site=site)
    assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "SITE_INVALID"


def test_form_options_list_only_free_field_staff_of_the_pm_unit(client, world):
    tool = _asset(client, world, "TL-OPT")
    options = client.get("/work-plans/form-options", headers=world.headers(client, "pm"))
    assert options.status_code == 200, options.text
    data = options.json()
    leaders = {p["id"] for p in data["leaders"]}
    assert {world.employees["leader"], world.employees["member"]} <= leaders
    assert world.employees["hr"] not in leaders                                   # akun kantor tidak tampil
    assert tool in {t["id"] for t in data["tools"]}
    assert {c["code"] for c in data["categories"]} == {"INSTALASI", "PEMELIHARAAN", "PERBAIKAN", "SURVEI", "LAINNYA"}


def test_edit_draft_rebuilds_content_and_requires_current_version(client, world):
    tool = _asset(client, world, "TL-EDT")
    plan_id = _create(client, world, tool_ids=[tool]).json()["plan"]["id"]
    headers = world.headers(client, "pm")

    stale = client.put(f"/work-plans/{plan_id}/full", headers=headers,
                       json=_body(world, days=1, row_version=_row_version(plan_id) - 1))
    assert stale.status_code == 409
    edited = client.put(f"/work-plans/{plan_id}/full", headers=headers,
                        json=_body(world, days=1, title="Survei ulang", category="SURVEI",
                                   row_version=_row_version(plan_id)))
    assert edited.status_code == 200, edited.text
    detail = _detail(client, world, plan_id)
    assert detail["plan"]["title"] == "Survei ulang" and detail["plan"]["category_label"] == "Survei"
    assert len(detail["days"]) == 1 and detail["assets"] == []                    # alat dilepas dari draf

    sync_query("UPDATE vms.work_plan SET status = 'PUBLISHED' WHERE id = %s", (plan_id,))
    locked = client.put(f"/work-plans/{plan_id}/full", headers=headers,
                        json=_body(world, days=1, row_version=_row_version(plan_id)))
    assert locked.status_code == 409 and locked.json()["error"]["code"] == "INVALID_STATE"
