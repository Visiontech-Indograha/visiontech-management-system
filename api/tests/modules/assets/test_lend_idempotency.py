"""Idempotency-Key opsional pada POST /assets/loans: header sama dua kali = satu data; tanpa header = perilaku lama."""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.modules.assets.test_asset_master import create_tool

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _lend(client, world: World, tool_id: str, key: str | None):
    headers = world.headers(client, "hr")
    if key:
        headers = {**headers, "Idempotency-Key": key}
    return client.post("/assets/loans", headers=headers,
                       json={"employee_id": world.employees["member"], "asset_type": "TOOL", "tool_id": tool_id})


def _count(tool_id: str) -> int:
    return int(sync_query("SELECT count(*) FROM asset_assignment WHERE tool_id = %s", (tool_id,))[0][0])


def test_same_key_twice_creates_one_loan(client, world: World):
    tool_id = create_tool(client, world, ownership="PERSONAL_LOAN").json()["tool_id"]
    key = uuid.uuid4().hex
    first = _lend(client, world, tool_id, key)
    second = _lend(client, world, tool_id, key)
    assert first.status_code == 201, first.text
    assert second.status_code == 201 and second.json() == first.json()
    assert _count(tool_id) == 1


def test_without_header_behaves_as_before(client, world: World):
    tool_id = create_tool(client, world, ownership="PERSONAL_LOAN").json()["tool_id"]
    assert _lend(client, world, tool_id, None).status_code == 201
    again = _lend(client, world, tool_id, None)
    assert again.json()["error"]["code"] == "ASSET_NOT_AVAILABLE"
    assert _count(tool_id) == 1
