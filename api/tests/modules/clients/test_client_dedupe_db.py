"""
Klien tidak terduplikasi: nama yang sama (abaikan huruf besar-kecil & spasi di ujung) ditolak 409 CLIENT_EXISTS
dengan id klien yang sudah ada. Daftar klien terbuka bagi pengelola rencana dan PM/OM/HR, tidak bagi lapangan.
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db

pytestmark = requires_db


def _make(client, world: World, name: str, who: str = "pm"):
    tag = uuid.uuid4().hex[:6]
    return client.post("/clients", headers=world.headers(client, who),
                       json={"client_code": f"UJI-{tag}", "name": name})


def test_same_name_in_other_case_or_padding_is_refused_with_existing_id(client, world: World):
    first = _make(client, world, f"Klien Dedupe {world.tag}")
    assert first.status_code == 201, first.text

    again = _make(client, world, f"  klien DEDUPE {world.tag}  ")
    assert again.status_code == 409, again.text
    error = again.json()["error"]
    assert error["code"] == "CLIENT_EXISTS"
    assert error["details"]["client_id"] == first.json()["client_id"]


def test_rename_onto_an_existing_name_is_refused(client, world: World):
    keep = _make(client, world, f"Klien Tetap {world.tag}").json()
    other = _make(client, world, f"Klien Lain {world.tag}").json()
    renamed = client.put(f"/clients/{other['client_id']}", headers=world.headers(client, "pm"),
                         json={"name": f"KLIEN TETAP {world.tag}"})
    assert renamed.status_code == 409, renamed.text
    assert renamed.json()["error"]["details"]["client_id"] == keep["client_id"]
    # mengganti nama menjadi nama barunya sendiri tetap boleh (tidak bentrok dengan dirinya sendiri)
    same = client.put(f"/clients/{keep['client_id']}", headers=world.headers(client, "pm"),
                      json={"name": f"klien tetap {world.tag}"})
    assert same.status_code == 200, same.text


def test_list_is_for_plan_managers_and_hr_only(client, world: World):
    _make(client, world, f"Klien Daftar {world.tag}")
    assert client.get("/clients", headers=world.headers(client, "pm")).status_code == 200
    assert client.get("/clients", headers=world.headers(client, "hr")).status_code == 200
    for who in ("member", "leader"):
        assert client.get("/clients", headers=world.headers(client, who)).status_code == 403, who
