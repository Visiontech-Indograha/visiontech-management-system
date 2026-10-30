"""
A10 · Peran ganda (T13): pemeriksaan peran memakai `has_role` (seluruh daftar peran), bukan `role` (peran pertama).
Pengguna yang memegang peran kedua PROJECT_MANAGER tetap dibatasi ke divisinya saat membuat jenis pekerjaan.
Akun uji diberi dua peran dengan memperluas `roles` pada identitas yang dibaca dari DB (satu-satunya tempat peran
dimuat; V2 hanya menyimpan satu `system_role`, jadi peran kedua hanya datang dari sumber ini).
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.modules.auth.repositories.auth_user_repository import CRUDUser
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


@pytest.fixture
def extra_roles(monkeypatch):
    """Tambahkan peran tambahan untuk akun tertentu: `extra_roles(user_id, ["PROJECT_MANAGER"])`."""
    original = CRUDUser.find_identity
    extra: dict[str, list[str]] = {}

    async def patched(self, user_id):
        row = await original(self, user_id)
        if row is None or str(user_id) not in extra:
            return row
        fields = dict(row._mapping)
        fields["roles"] = [*fields["roles"], *extra[str(user_id)]]
        return SimpleNamespace(**fields)

    monkeypatch.setattr(CRUDUser, "find_identity", patched)

    def _grant(user_id: str, roles: list[str]) -> None:
        extra[str(user_id)] = roles

    return _grant


def _second_division(world: World) -> str:
    unit = world.add_unit(f"Lain {uuid.uuid4().hex[:4]}")
    other_pm = world.add_person(f"pm_lain_{uuid.uuid4().hex[:4]}", "PM", unit_id=unit)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (other_pm, unit))
    return unit


def test_dual_role_user_is_scoped_as_pm_when_creating_work_type(client, world: World, extra_roles):
    """Akun ber-peran EMPLOYEE (utama) + PROJECT_MANAGER (kedua) hanya boleh membuat jenis pekerjaan di divisinya."""
    dual = world.add_person("ganda", None, unit_id=world.unit_id)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (dual, world.unit_id))
    extra_roles(world.users["ganda"], ["PROJECT_MANAGER"])
    other_unit = _second_division(world)

    response = client.post("/work-types", headers=world.headers(client, "ganda"),
                           json={"name": f"Jenis ganda {world.tag}", "division_id": other_unit, "kind": "WORK"})

    assert response.status_code == 403, response.text


def test_dual_role_user_still_creates_work_type_in_own_division(client, world: World, extra_roles):
    dual = world.add_person("ganda2", None, unit_id=world.unit_id)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (dual, world.unit_id))
    extra_roles(world.users["ganda2"], ["PROJECT_MANAGER"])

    response = client.post("/work-types", headers=world.headers(client, "ganda2"),
                           json={"name": f"Jenis milik {world.tag}", "division_id": world.unit_id, "kind": "WORK"})

    assert response.status_code == 201, response.text


def test_plain_employee_is_still_refused_outside_scope(client, world: World):
    """Pembanding: karyawan tanpa peran PM tetap ditolak membuat jenis pekerjaan (tidak ada perubahan perilaku)."""
    response = client.post("/work-types", headers=world.headers(client, "member"),
                           json={"name": f"Jenis biasa {world.tag}", "division_id": world.unit_id, "kind": "WORK"})

    assert response.status_code in (401, 403), response.text
