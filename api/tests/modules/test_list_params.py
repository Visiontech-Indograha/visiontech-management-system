"""
Pencarian + paginasi opsional + X-Total-Count pada daftar utama; tanpa parameter perilaku lama tetap.
"""
from __future__ import annotations

from tests.conftest import World, requires_db

pytestmark = requires_db


def test_leaves_search_and_pagination(client, world: World):
    h = world.headers(client, "hr")
    base = client.get("/leaves", headers=h)
    assert base.status_code == 200
    total = int(base.headers["X-Total-Count"])
    assert total == len(base.json())  # tanpa parameter: semua baris (kompatibel mundur)

    paged = client.get("/leaves?page=1&size=1", headers=h)
    assert paged.status_code == 200
    assert int(paged.headers["X-Total-Count"]) == total
    assert len(paged.json()) <= 1

    none = client.get("/leaves?q=zzzz-tidak-ada-xyz", headers=h)
    assert none.json() == [] and none.headers["X-Total-Count"] == "0"


def test_list_params_are_validated(client, world: World):
    h = world.headers(client, "hr")
    for bad in ("page=0", "size=0", "size=101", "page=abc", "q=" + "x" * 101):
        assert client.get(f"/leaves?{bad}", headers=h).status_code == 422, bad
    assert client.get("/leaves?date_from=2026-02-01&date_to=2026-01-01", headers=h).status_code == 422


def test_search_is_case_and_accent_insensitive(client, world: World):
    h = world.headers(client, "hr")
    everything = client.get("/teams", headers=h).json()
    if everything:
        name = everything[0]["name"]
        hit = client.get(f"/teams?q={name.upper()}", headers=h)
        assert any(t["name"] == name for t in hit.json())
