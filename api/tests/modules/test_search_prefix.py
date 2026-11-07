"""Putusan pemilik: pencarian `q` = awalan (bukan 'mengandung'); % dan _ dibaca harfiah."""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db

pytestmark = requires_db


def _names(response) -> list[str]:
    assert response.status_code == 200, response.text
    body = response.json()
    items = body["items"] if isinstance(body, dict) else body
    return [i["name"] if "name" in i else i["full_name"] for i in items]


def _client(client, world: World, name: str, code: str) -> None:
    made = client.post("/clients", headers=world.headers(client, "pm"),
                       json={"client_code": code, "name": name, "pic_name": "Budi"})
    assert made.status_code == 201, made.text


def test_client_search_is_prefix_and_literal(client, world: World):
    tag = uuid.uuid4().hex[:6]
    _client(client, world, f"Zeta{tag} Mandiri", f"ZK{tag}")
    _client(client, world, f"Yota{tag}_100%", f"YK{tag}")
    h = world.headers(client, "pm")

    def find(q: str) -> list[str]:
        return _names(client.get("/clients", headers=h, params={"q": q}))

    assert find(f"zeta{tag}") == [f"Zeta{tag} Mandiri"]
    assert find("mandiri") == []  # tengah nama tak cocok
    assert find(f"YK{tag}") == [f"Yota{tag}_100%"]  # awalan kode
    assert find(f"Yota{tag}_1") == [f"Yota{tag}_100%"]
    assert find(f"Yota{tag}x") == []
    assert find("%") == []
    assert find("_") == []


def test_employee_search_is_prefix(client, world: World):
    h = world.headers(client, "hr")
    params = {"office_id": world.org_id, "size": 100}

    def find(q: str) -> list[str]:
        return _names(client.get("/employees", headers=h, params={**params, "q": q}))

    assert len(find("karyawan uji pm")) == 1  # awalan cocok
    assert find("uji pm") == []  # tengah nama tak cocok
    assert len(find(world.logins["pm"][:8])) >= 1  # awalan email
    assert find(world.logins["pm"].split("@")[1]) == []  # bagian tengah/belakang email
    assert find("%") == []
    assert find("_") == []
