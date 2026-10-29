"""
Pengajuan pinjam aset oleh karyawan (HR/GA menyetujui) dan pengajuan pengembalian dengan foto kondisi.
Alur: member mengajukan → hr menyetujui (serah terima otomatis) → member mengajukan kembali + foto →
hr mengonfirmasi lewat pengembalian biasa.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db
from tests.modules.assets.test_asset_master import create_tool, upload

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _request(client, world: World, tool_id: str, who: str = "member", purpose: str = "Pasang kamera di lokasi"):
    return client.post("/assets/loan-requests", headers=world.headers(client, who),
                       json={"asset_type": "TOOL", "tool_id": tool_id, "purpose": purpose})


def _tool(client, world: World) -> str:
    created = create_tool(client, world)
    assert created.status_code == 201, created.text
    return created.json()["tool_id"]


def test_request_approve_return_cycle(client, world: World):
    tool_id = _tool(client, world)
    created = _request(client, world, tool_id)
    assert created.status_code == 201, created.text
    request_id = created.json()["request_id"]
    assert created.json()["status"] == "PENDING"
    assert created.json()["employee_id"] == world.employees["member"]

    hr = world.headers(client, "hr")
    approved = client.post(f"/assets/loan-requests/{request_id}/review", headers=hr, json={"decision": "APPROVED"})
    assert approved.status_code == 200, approved.text
    assignment_id = approved.json()["assignment_id"]
    assert approved.json()["status"] == "APPROVED" and assignment_id

    member = world.headers(client, "member")
    loans = client.get("/assets/loans", headers=member).json()
    assert [loan["assignment_id"] for loan in loans] == [assignment_id]

    photo = upload(client, world, "member")
    asked = client.post(f"/assets/loans/{assignment_id}/return-request", headers=member,
                        json={"condition": "damaged", "note": "Mata bor patah", "photo_file_id": photo})
    assert asked.status_code == 200, asked.text
    assert asked.json()["return_condition"] == "damaged" and asked.json()["return_file_id"] == photo
    assert asked.json()["returned_at"] is None

    done = client.post(f"/assets/loans/{assignment_id}/return", headers=hr, json={"condition": "damaged"})
    assert done.status_code == 200 and done.json()["returned_at"] is not None


def test_employee_sees_only_own_requests(client, world: World):
    tool_id = _tool(client, world)
    request_id = _request(client, world, tool_id).json()["request_id"]
    mine = client.get("/assets/loan-requests", headers=world.headers(client, "member")).json()
    assert [r["request_id"] for r in mine] == [request_id]
    assert client.get("/assets/loan-requests", headers=world.headers(client, "leader")).json() == []
    everything = client.get("/assets/loan-requests", headers=world.headers(client, "hr")).json()
    assert request_id in [r["request_id"] for r in everything]


def test_only_asset_manager_can_review(client, world: World):
    request_id = _request(client, world, _tool(client, world)).json()["request_id"]
    response = client.post(f"/assets/loan-requests/{request_id}/review", headers=world.headers(client, "leader"),
                           json={"decision": "APPROVED"})
    assert response.status_code == 403


def test_rejected_request_does_not_lend(client, world: World):
    tool_id = _tool(client, world)
    request_id = _request(client, world, tool_id).json()["request_id"]
    rejected = client.post(f"/assets/loan-requests/{request_id}/review", headers=world.headers(client, "hr"),
                           json={"decision": "REJECTED", "note": "Dipakai tim lain"})
    assert rejected.json()["status"] == "REJECTED" and rejected.json()["assignment_id"] is None
    loans = client.get("/assets/loans", headers=world.headers(client, "hr")).json()
    assert tool_id not in [loan["asset_id"] for loan in loans]
    again = client.post(f"/assets/loan-requests/{request_id}/review", headers=world.headers(client, "hr"),
                        json={"decision": "APPROVED"})
    assert again.json()["error"]["code"] == "ALREADY_DECIDED"


def test_owner_cancels_pending_only(client, world: World):
    request_id = _request(client, world, _tool(client, world)).json()["request_id"]
    other = client.post(f"/assets/loan-requests/{request_id}/cancel", headers=world.headers(client, "leader"))
    assert other.status_code == 403
    mine = client.post(f"/assets/loan-requests/{request_id}/cancel", headers=world.headers(client, "member"))
    assert mine.json()["status"] == "CANCELLED"
    twice = client.post(f"/assets/loan-requests/{request_id}/cancel", headers=world.headers(client, "member"))
    assert twice.json()["error"]["code"] == "NOT_CANCELLABLE"


def test_duplicate_pending_request_is_blocked(client, world: World):
    tool_id = _tool(client, world)
    assert _request(client, world, tool_id).status_code == 201
    assert _request(client, world, tool_id).json()["error"]["code"] == "REQUEST_EXISTS"


def test_only_holder_can_ask_return(client, world: World):
    tool_id = _tool(client, world)
    request_id = _request(client, world, tool_id).json()["request_id"]
    assignment_id = client.post(f"/assets/loan-requests/{request_id}/review", headers=world.headers(client, "hr"),
                                json={"decision": "APPROVED"}).json()["assignment_id"]
    photo = upload(client, world, "leader")
    stranger = client.post(f"/assets/loans/{assignment_id}/return-request", headers=world.headers(client, "leader"),
                           json={"condition": "ready", "photo_file_id": photo})
    assert stranger.status_code == 403
