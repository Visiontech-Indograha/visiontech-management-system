"""Putusan pemilik (10 Nov 2026): daftar LAMA tetap 'mengandung kata'; % dan _ dibaca harfiah."""
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


def test_client_search_contains_and_literal(client, world: World):
    tag = uuid.uuid4().hex[:6]
    _client(client, world, f"Zeta{tag} Mandiri", f"ZK{tag}")
    _client(client, world, f"Yota{tag}_100%", f"YK{tag}")
    h = world.headers(client, "pm")

    def find(q: str) -> list[str]:
        return _names(client.get("/clients", headers=h, params={"q": q}))

    assert find(f"zeta{tag}") == [f"Zeta{tag} Mandiri"]
    assert f"Zeta{tag} Mandiri" in find("mandiri")  # tengah nama cocok
    assert find(f"YK{tag}") == [f"Yota{tag}_100%"]  # awalan kode
    assert find(f"Yota{tag}_1") == [f"Yota{tag}_100%"]
    assert find(f"Yota{tag}x") == []
    assert find(f"{tag}_1") == [f"Yota{tag}_100%"]  # _ harfiah di tengah
    assert f"Yota{tag}_100%" in find("0%")
    assert all("%" in n for n in find("%"))  # harfiah, bukan wildcard
    assert all("_" in n for n in find("_"))  # harfiah, bukan wildcard


def test_employee_search_contains(client, world: World):
    h = world.headers(client, "hr")
    params = {"office_id": world.org_id, "size": 100}

    def find(q: str) -> list[str]:
        return _names(client.get("/employees", headers=h, params={**params, "q": q}))

    assert len(find("karyawan uji pm")) == 1  # awalan cocok
    assert len(find("uji pm")) == 1  # tengah nama cocok
    assert len(find(world.logins["pm"][:8])) >= 1  # awalan email
    assert find("%") == []  # harfiah, bukan wildcard
    assert find("_") == []
    assert all("_" in n for n in find("_"))  # harfiah, bukan wildcard
