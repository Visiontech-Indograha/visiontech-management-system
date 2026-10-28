"""Usulan nomor karyawan berikutnya: awalan/lebar dari karyawan terbaru, angka = maksimum + 1."""
from __future__ import annotations

import asyncio

from app.modules.employees.services.employee_service import EmployeeService
from tests.conftest import World, requires_db


class _Repo:
    def __init__(self, nos: list[str]) -> None:
        self.nos = nos

    async def recent_employee_nos(self, limit: int = 300) -> list[str]:
        return self.nos


def _next(nos: list[str]) -> str:
    svc = EmployeeService.__new__(EmployeeService)
    svc.repo = _Repo(nos)  # type: ignore[assignment]
    return asyncio.run(svc.next_employee_no())


def test_follows_prefix_and_width_of_the_newest() -> None:
    assert _next(["VMS-EMP-011", "VMS-EMP-010", "NYATA-024"]) == "VMS-EMP-012"


def test_uses_highest_number_of_that_prefix_and_keeps_width() -> None:
    assert _next(["A-07", "A-120", "A-9"]) == "A-121"
    assert _next(["K007", "K009"]) == "K010"


def test_empty_or_unnumbered_falls_back() -> None:
    assert _next([]) == "EMP-001"
    assert _next(["ABC", "XYZ"]) == "EMP-001"


@requires_db
def test_endpoint_is_for_user_managers_only(client, world: World) -> None:
    ok = client.get("/employees/next-no", headers=world.headers(client, "hr"))
    assert ok.status_code == 200, ok.text
    assert ok.json()["employee_no"]
    assert client.get("/employees/next-no", headers=world.headers(client, "member")).status_code == 403
