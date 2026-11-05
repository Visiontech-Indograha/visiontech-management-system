"""Nonaktifkan dokumen (POST /deactivate) tidak menimpa status yang diubah pihak lain (compare-and-set)."""
from __future__ import annotations

import pytest

from tests.concurrency import tahan_lalu_ubah
from tests.conftest import World, requires_db, sync_query
from tests.modules.documents.test_document_rules import _upload

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def test_nonaktifkan_dokumen_yang_tertahan_dapat_409_dan_tidak_menimpa(client, world: World):
    doc = _upload(client, world).json()["id"]
    emp = world.employees["member"]
    hasil = tahan_lalu_ubah(
        "UPDATE employee_file SET status = 'extended' WHERE employee_file_id = %s", (doc,),
        lambda: client.post(f"/employees/{emp}/documents/{doc}/deactivate", headers=world.headers(client, "hr")),
    )
    assert hasil.status_code == 409, hasil.text
    assert hasil.json()["error"]["code"] == "INVALID_STATE", hasil.text
    status = sync_query("SELECT status::text FROM employee_file WHERE employee_file_id = %s", (doc,))[0][0]
    assert status == "extended"
