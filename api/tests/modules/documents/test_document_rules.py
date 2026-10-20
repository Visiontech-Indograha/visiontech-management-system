"""
Milestone 3 · Dokumen karyawan (employee 1─N employee_file). HR/GA mencatat dokumen dari berkas yang
sudah diunggah; karyawan hanya melihat dokumennya sendiri; dokumen sejenis yang baru menggantikan yang lama.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.conftest import World, requires_db, sync_query

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _file(client, world: World, colour: int) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (colour, 40, 90)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, "hr"),
                           files={"file": ("dok.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def _upload(client, world: World, owner: str = "member", doc_type: str = "SIM A", colour: int = 1, who: str = "hr"):
    return client.post(f"/employees/{world.employees[owner]}/documents", headers=world.headers(client, who),
                       json={"doc_type": doc_type, "file_id": _file(client, world, colour),
                             "expired_at": "2030-01-01"})


def _status(doc_id: str) -> str:
    return sync_query("SELECT status::text FROM employee_file WHERE employee_file_id = %s", (doc_id,))[0][0]


def test_hr_records_document_and_owner_sees_it(client, world: World):
    created = _upload(client, world)
    assert created.status_code == 201, created.text
    doc = created.json()
    assert (doc["doc_type"], doc["status"], doc["expired_at"]) == ("SIM_A", "active", "2030-01-01")
    assert doc["file_id"] is not None

    mine = client.get(f"/employees/{world.employees['member']}/documents", headers=world.headers(client, "member"))
    assert [d["id"] for d in mine.json()["items"]] == [doc["id"]]


def test_employee_cannot_see_others_or_record_documents(client, world: World):
    _upload(client, world, owner="leader")
    assert client.get(f"/employees/{world.employees['leader']}/documents",
                      headers=world.headers(client, "member")).status_code == 404
    response = client.post(f"/employees/{world.employees['member']}/documents",
                           headers=world.headers(client, "member"),
                           json={"doc_type": "KTP", "file_id": _file(client, world, 9)})
    assert response.status_code == 403


def test_new_document_of_same_type_extends_the_old_one(client, world: World):
    old = _upload(client, world, colour=1).json()["id"]
    new = _upload(client, world, colour=2).json()["id"]
    other = _upload(client, world, doc_type="KTP", colour=3).json()["id"]
    assert (_status(old), _status(new), _status(other)) == ("extended", "active", "active")


def test_unknown_file_is_rejected(client, world: World):
    response = client.post(f"/employees/{world.employees['member']}/documents", headers=world.headers(client, "hr"),
                           json={"doc_type": "KTP", "file_id": "01a0dd8d-b442-7c07-91b8-5d8ac8f059fb"})
    assert response.status_code == 422


def test_deactivate_and_delete(client, world: World):
    hr = world.headers(client, "hr")
    base = f"/employees/{world.employees['member']}/documents"
    doc_id = _upload(client, world).json()["id"]
    assert client.post(f"{base}/{doc_id}/deactivate", headers=hr).json()["status"] == "not_active"
    assert client.delete(f"{base}/{doc_id}", headers=hr).status_code == 200
    assert client.get(base, headers=hr).json()["total"] == 0
    # Dokumen karyawan lain tidak bisa diubah lewat URL karyawan ini.
    foreign = _upload(client, world, owner="leader").json()["id"]
    assert client.delete(f"{base}/{foreign}", headers=hr).status_code == 404
