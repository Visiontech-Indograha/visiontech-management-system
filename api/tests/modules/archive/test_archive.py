"""B-29 · Arsip & Pulihkan: matriks peran, pemulihan idempoten, konflik unik (409), induk diarsipkan, audit."""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.modules.assets.test_asset_master import create_tool

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _soft_delete(table: str, pk: str, item_id: str) -> None:
    sync_query(f"UPDATE {table} SET delete_at = now() WHERE {pk} = %s", (item_id,))


def _deleted_at(table: str, pk: str, item_id: str):
    return sync_query(f"SELECT delete_at FROM {table} WHERE {pk} = %s", (item_id,))[0][0]


@pytest.fixture
def made():
    """Catat id klien/jabatan/mess buatan uji lalu hapus bersih (purge kantor tidak mencakupnya)."""
    ids: dict[str, list[str]] = {"client": [], "job_position": [], "company_mess": []}
    yield ids
    for table, pk in (("client", "client_id"), ("job_position", "position_id"), ("company_mess", "mess_id")):
        for item in ids[table]:
            sync_query(f"DELETE FROM {table} WHERE {pk} = %s", (item,))


def _client(made, world: World, code: str | None = None, name: str | None = None) -> str:
    cid = str(sync_query(
        "INSERT INTO client (client_code, name) VALUES (%s, %s) RETURNING client_id",
        (code or f"C{world.tag}", name or f"Klien {world.tag}"))[0][0])
    made["client"].append(cid)
    return cid


def test_role_matrix_on_archive_list(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    _soft_delete("tool", "tool_id", tool_id)
    for who, expected in (("admin", 200), ("ops", 403), ("hr", 200), ("pm", 403), ("leader", 403), ("member", 403)):
        response = client.get("/archive/tools", headers=world.headers(client, who))
        assert response.status_code == expected, (who, response.text)
    ids = [r["id"] for r in client.get("/archive/tools", headers=world.headers(client, "hr")).json()]
    assert tool_id in ids
    assert client.post(f"/archive/tools/{tool_id}/restore", headers=world.headers(client, "member")).status_code == 403


def test_pm_cannot_see_or_restore_clients(client, world: World, made):
    cid = _client(made, world)
    _soft_delete("client", "client_id", cid)
    assert client.get("/archive/clients", headers=world.headers(client, "pm")).status_code == 403
    assert client.post(f"/archive/clients/{cid}/restore", headers=world.headers(client, "pm")).status_code == 403
    assert _deleted_at("client", "client_id", cid) is not None


def test_restore_tool_is_idempotent_and_audited(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    _soft_delete("tool", "tool_id", tool_id)
    headers = world.headers(client, "hr")
    first = client.post(f"/archive/tools/{tool_id}/restore", headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["id"] == tool_id and first.json()["deleted_at"] is None
    assert _deleted_at("tool", "tool_id", tool_id) is None
    again = client.post(f"/archive/tools/{tool_id}/restore", headers=headers)
    assert again.status_code == 200
    logs = sync_query("SELECT count(*) FROM app_activity_logs WHERE action = 'TOOL_RESTORE' AND entity_id = %s",
                      (tool_id,))[0][0]
    assert logs == 1  # pemulihan kedua tidak mencatat ulang
    assert tool_id not in [r["id"] for r in client.get("/archive/tools", headers=headers).json()]


def test_unknown_id_is_404(client, world: World):
    response = client.post(f"/archive/tools/{uuid.uuid4()}/restore", headers=world.headers(client, "hr"))
    assert response.status_code == 404


def test_tool_code_conflict_is_409(client, world: World):
    old = create_tool(client, world, code="tl-arsip-dup").json()["tool_id"]
    _soft_delete("tool", "tool_id", old)
    assert create_tool(client, world, code="tl-arsip-dup").status_code == 201
    response = client.post(f"/archive/tools/{old}/restore", headers=world.headers(client, "hr"))
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "RESTORE_CONFLICT"
    assert _deleted_at("tool", "tool_id", old) is not None


def test_client_restore_and_name_conflict(client, world: World, made):
    headers = world.headers(client, "admin")
    cid = _client(made, world, code=f"A{world.tag}", name=f"Klien Arsip {world.tag}")
    _soft_delete("client", "client_id", cid)
    assert cid in [r["id"] for r in client.get("/archive/clients", headers=headers).json()]
    assert client.post(f"/archive/clients/{cid}/restore", headers=headers).status_code == 200
    assert _deleted_at("client", "client_id", cid) is None

    gone = _client(made, world, code=f"B{world.tag}", name=f"  klien ARSIP {world.tag} ")
    _soft_delete("client", "client_id", gone)
    conflict = client.post(f"/archive/clients/{gone}/restore", headers=headers)
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "RESTORE_CONFLICT"


def test_job_position_code_conflict_and_parent_archived(client, world: World, made):
    headers = world.headers(client, "admin")
    code = f"J{world.tag}"
    pid = str(sync_query("INSERT INTO job_position (code, name) VALUES (%s, 'Teknisi') RETURNING position_id",
                         (code,))[0][0])
    made["job_position"].append(pid)
    _soft_delete("job_position", "position_id", pid)
    other = str(sync_query("INSERT INTO job_position (code, name) VALUES (%s, 'Teknisi 2') RETURNING position_id",
                           (code,))[0][0])
    made["job_position"].append(other)
    assert client.post(f"/archive/job-positions/{pid}/restore", headers=headers).status_code == 409
    sync_query("UPDATE job_position SET code = %s WHERE position_id = %s", (f"Z{world.tag}", other))
    sync_query("UPDATE job_position SET division_id = %s WHERE position_id = %s", (world.unit_id, pid))
    _soft_delete("division", "division_id", world.unit_id)
    blocked = client.post(f"/archive/job-positions/{pid}/restore", headers=headers)
    assert blocked.status_code == 409, blocked.text
    sync_query("UPDATE division SET delete_at = NULL WHERE division_id = %s", (world.unit_id,))
    assert client.post(f"/archive/job-positions/{pid}/restore", headers=headers).status_code == 200


def test_division_and_mess_restore(client, world: World, made):
    headers = world.headers(client, "admin")
    unit = world.add_unit("Arsip")
    _soft_delete("division", "division_id", unit)
    assert client.post(f"/archive/divisions/{unit}/restore", headers=headers).status_code == 200
    mess = str(sync_query(
        "INSERT INTO company_mess (mess_name, city, address) VALUES (%s, 'Kota', 'Jl. Uji') RETURNING mess_id",
        (f"Mess {world.tag}",))[0][0])
    made["company_mess"].append(mess)
    _soft_delete("company_mess", "mess_id", mess)
    listed = client.get("/archive/mess", headers=headers)
    assert listed.status_code == 200 and mess in [r["id"] for r in listed.json()]
    assert client.post(f"/archive/mess/{mess}/restore", headers=headers).status_code == 200
    assert client.post(f"/archive/mess/{mess}/restore", headers=world.headers(client, "pm")).status_code == 403


def test_list_search_and_pagination_header(client, world: World, made):
    headers = world.headers(client, "admin")
    for i in range(3):
        cid = _client(made, world, code=f"P{i}{world.tag}", name=f"Zeta{world.tag} {i}")
        _soft_delete("client", "client_id", cid)
    response = client.get(f"/archive/clients?q=zeta{world.tag}&page=1&size=2", headers=headers)
    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "3" and len(response.json()) == 2
    assert client.get("/archive/clients?size=500", headers=headers).status_code == 422
