"""
A3 · Klien: daftar hanya untuk pengelola rencana (CREATE_PLAN), dan klien yang sudah punya proyek hanya diubah
PM/OM divisi pemilik proyek. Pekerja lapangan & ketua tim tak melihat daftar klien (memuat PIC).
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _client_with_project(client, world: World) -> str:
    tag = uuid.uuid4().hex[:6]
    made = client.post("/clients", headers=world.headers(client, "pm"),
                       json={"client_code": f"UJI-{tag}", "name": f"Klien uji {tag}", "pic_name": "Budi"})
    assert made.status_code == 201, made.text
    client_id = made.json()["client_id"]
    body = {"client_id": client_id, "office_id": world.org_id, "division_id": world.unit_id,
            "spk_number": f"SPK/UJI/{tag}", "project_title": "Proyek uji klien", "total_target_qty": "5",
            "unit_measure": "Unit", "start_date": "2026-11-01", "end_date": "2026-12-01"}
    created = client.post("/projects", headers=world.headers(client, "pm"), json=body)
    assert created.status_code == 201, created.text
    return client_id


def test_client_list_only_for_plan_managers(client, world: World):
    _client_with_project(client, world)
    assert client.get("/clients", headers=world.headers(client, "pm")).status_code == 200
    for who in ("member", "leader"):
        denied = client.get("/clients", headers=world.headers(client, who))
        assert denied.status_code == 403, (who, denied.text)


def test_client_with_project_updated_only_by_owning_division(client, world: World):
    client_id = _client_with_project(client, world)
    unit2 = world.add_unit("Dua")
    pm2 = world.add_person("pm2", "PM", unit_id=unit2)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (pm2, unit2))

    new_name = f"Ganti {uuid.uuid4().hex[:8]}"  # nama unik: DB uji dipakai bersama (nama klien harus unik)
    denied = client.put(f"/clients/{client_id}", headers=world.headers(client, "pm2"), json={"name": new_name})
    assert denied.status_code == 403, denied.text
    assert client.delete(f"/clients/{client_id}", headers=world.headers(client, "pm2")).status_code == 403

    allowed = client.put(f"/clients/{client_id}", headers=world.headers(client, "pm"), json={"name": new_name})
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["name"] == new_name
