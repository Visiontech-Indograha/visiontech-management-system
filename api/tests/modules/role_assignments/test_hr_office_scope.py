"""
Izin khusus HR/Finance di luar absensi dibatasi ke kantor tugas (ADR 0002; docs/audit-izin-hr-finance-per-kantor.md):
paritas flag mati, HR kantor sendiri, HR + penugasan kantor lain, OM+HR (HR tidak melebar), SA/OM tidak dibatasi.
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from tests.conftest import World, requires_db

pytestmark = requires_db

HR, OM = "ADMIN_HR_GA", "OPERATIONAL_MANAGER"


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)


def _face(client, viewer_world: World, viewer: str, emp_id: str) -> int:
    return client.get(f"/face/enrollments/{emp_id}/status", headers=viewer_world.headers(client, viewer)).status_code


def _docs(client, viewer_world: World, viewer: str, emp_id: str) -> int:
    return client.get(f"/employees/{emp_id}/documents", headers=viewer_world.headers(client, viewer)).status_code


def _assign(client, world: World, who: str, role: str, office: str | None) -> None:
    r = client.post(f"/users/{world.users[who]}/role-assignments", headers=world.headers(client, "admin"),
                    json={"role": role, "office_id": office})
    assert r.status_code == 201, r.text


def test_flag_off_hr_unchanged(client, world: World, other_world: World, flag_off):
    """Paritas: flag mati = HR menjangkau karyawan semua kantor seperti sebelumnya."""
    for fn in (_face, _docs):
        assert fn(client, world, "hr", world.employees["member"]) == 200
        assert fn(client, world, "hr", other_world.employees["member"]) == 200


def test_flag_on_hr_only_own_office(client, world: World, other_world: World, flag_on):
    for fn in (_face, _docs):
        assert fn(client, world, "hr", world.employees["member"]) == 200
        assert fn(client, world, "hr", other_world.employees["member"]) == 404


def test_flag_on_hr_with_assignment_reaches_other_office(client, world: World, other_world: World, flag_on):
    _assign(client, world, "hr", HR, other_world.org_id)
    for fn in (_face, _docs):
        assert fn(client, world, "hr", other_world.employees["member"]) == 200


def test_flag_on_om_with_hr_assignment_hr_permission_not_widened(client, world: World, other_world: World, flag_on):
    """OM yang juga HR kantor A: izin khusus HR (kelola user) hanya kantor A, walau OM melihat semua kantor."""
    _assign(client, world, "ops", HR, world.org_id)
    assert _face(client, world, "ops", world.employees["member"]) == 200
    assert _face(client, world, "ops", other_world.employees["member"]) == 404


def test_flag_on_super_admin_unrestricted(client, world: World, other_world: World, flag_on):
    assert _face(client, world, "admin", other_world.employees["member"]) == 200
    assert _docs(client, world, "admin", other_world.employees["member"]) == 200


def test_flag_on_hr_cannot_move_employee_to_foreign_office(client, world: World, other_world: World, flag_on):
    r = client.put(f"/employees/{world.employees['member']}", headers=world.headers(client, "hr"),
                   json={"office_id": other_world.org_id})
    assert r.status_code == 404, r.text
