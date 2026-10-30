"""
Salin jenis pekerjaan lintas divisi (POST /work-types/{id}/copy-to-division): slot foto dan BoM default ikut disalin;
PM hanya boleh menyalin ke divisinya sendiri; nama kembar di divisi tujuan ditolak.
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _second_division(world: World) -> str:
    unit = world.add_unit(f"Salin {uuid.uuid4().hex[:4]}")
    other_pm = world.add_person(f"pm_salin_{uuid.uuid4().hex[:4]}", "PM", unit_id=unit)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (other_pm, unit))
    return unit


def _template(client, world: World, headers: dict) -> str:
    body = {
        "name": f"Jenis sumber {world.tag}",
        "kind": "WORK",
        "photos": [
            {"label": "Foto depan", "hint": "Tampak depan", "required": True},
            {"label": "Foto label", "required": False},
        ],
    }
    created = client.post("/work-types", headers=headers, json=body)
    assert created.status_code == 201, created.text
    type_id = created.json()["id"]
    material = client.post(
        f"/work-types/{type_id}/materials", headers=headers,
        json={"material_name": "Kabel UTP", "default_qty": 2, "unit": "Meter", "material_code": "KBL-1"},
    )
    assert material.status_code == 201, material.text
    return type_id


def test_copy_work_type_to_other_division_keeps_photos_and_bom(client, world: World):
    admin = world.headers(client, "admin")
    source = _template(client, world, admin)
    target_division = _second_division(world)

    copied = client.post(f"/work-types/{source}/copy-to-division", headers=admin,
                         json={"division_id": target_division})

    assert copied.status_code == 201, copied.text
    body = copied.json()
    assert body["id"] != source
    assert body["division_id"] == target_division
    assert [p["label"] for p in body["photos"]] == ["Foto depan", "Foto label"]
    assert body["photos"][0]["hint"] == "Tampak depan"
    materials = client.get(f"/work-types/{body['id']}/materials", headers=admin).json()
    assert [(m["material_name"], m["unit"], m["default_qty"]) for m in materials] == [("Kabel UTP", "Meter", 2.0)]
    # Sumber tidak berubah.
    source_materials = client.get(f"/work-types/{source}/materials", headers=admin).json()
    assert len(source_materials) == 1


def test_pm_cannot_copy_into_other_division(client, world: World):
    admin = world.headers(client, "admin")
    source = _template(client, world, admin)
    other_division = _second_division(world)
    pm = world.headers(client, "pm")

    response = client.post(f"/work-types/{source}/copy-to-division", headers=pm,
                           json={"division_id": other_division})

    assert response.status_code == 403, response.text


def test_copy_refuses_duplicate_name_in_target_division(client, world: World):
    admin = world.headers(client, "admin")
    source = _template(client, world, admin)
    target_division = _second_division(world)
    first = client.post(f"/work-types/{source}/copy-to-division", headers=admin,
                        json={"division_id": target_division})
    assert first.status_code == 201, first.text

    again = client.post(f"/work-types/{source}/copy-to-division", headers=admin,
                        json={"division_id": target_division})

    assert again.status_code == 409, again.text
