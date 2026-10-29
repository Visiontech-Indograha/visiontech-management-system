"""
Notifikasi PM/OM divisi memakai division.pm_id / om_id divisi karyawan (bukan employee.division_id PM),
sehingga PM yang memimpin beberapa divisi menerima notifikasi tiap divisinya.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.modules.notifications.services.notification_service import NotificationService


async def test_division_managers_are_resolved_from_the_employees_division():
    svc = NotificationService(MagicMock())
    svc.repo = MagicMock()
    svc.repo.employee_division = AsyncMock(return_value=SimpleNamespace(office_id="kantor-1", division_id="div-2"))
    svc.repo.division_manager_user_ids = AsyncMock(return_value=["user-pm-div2"])
    svc.repo.insert_for_users = AsyncMock()

    await svc.notify_division_managers("emp-1", "LEAVE_REQUESTED", "Judul", "isi", target="leave")

    args = svc.repo.division_manager_user_ids.await_args.args
    assert args[0] == "div-2"
    assert "PROJECT_MANAGER" in args[1] and "OPERATIONAL_MANAGER" in args[1]
    svc.repo.insert_for_users.assert_awaited_once()
    assert svc.repo.insert_for_users.await_args.args[0] == ["user-pm-div2"]


async def test_employee_without_division_notifies_nobody():
    svc = NotificationService(MagicMock())
    svc.repo = MagicMock()
    svc.repo.employee_division = AsyncMock(return_value=SimpleNamespace(office_id="kantor-1", division_id=None))
    svc.repo.division_manager_user_ids = AsyncMock()
    svc.repo.insert_for_users = AsyncMock()

    await svc.notify_division_managers("emp-1", "LEAVE_REQUESTED", "Judul")

    svc.repo.division_manager_user_ids.assert_not_awaited()
    svc.repo.insert_for_users.assert_not_awaited()
