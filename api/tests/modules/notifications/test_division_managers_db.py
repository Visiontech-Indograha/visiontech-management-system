"""
Uji DB: SQL penerima notifikasi divisi (division.pm_id / om_id) berjalan terhadap skema nyata.
"""
from __future__ import annotations

import asyncio

from app.database.session import AsyncSessionLocal
from app.modules.notifications.repositories.notification_repository import NotificationRepository
from tests.conftest import World, requires_db

pytestmark = requires_db

MANAGER_ROLES = ("PROJECT_MANAGER", "OPERATIONAL_MANAGER")


def _division_manager_ids(division_id: str) -> list[str]:
    async def run() -> list[str]:
        async with AsyncSessionLocal() as db:
            return await NotificationRepository(db).division_manager_user_ids(division_id, MANAGER_ROLES)

    return asyncio.run(run())


def test_pm_and_om_of_every_division_they_lead_are_resolved(world: World):
    second = world.add_unit("Dua")  # divisi kedua: PM dan OM dunia uji yang sama
    ids = _division_manager_ids(second)
    assert world.users["pm"] in ids
    assert world.users["ops"] in ids
    assert world.users["leader"] not in ids  # ketua tim bukan PM/OM
    assert world.users["member"] not in ids


def test_unknown_division_has_no_recipients(world: World):
    assert _division_manager_ids("00000000-0000-4000-8000-0000000000d9") == []
