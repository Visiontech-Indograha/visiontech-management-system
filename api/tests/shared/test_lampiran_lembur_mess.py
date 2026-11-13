"""
Lampiran pengajuan lembur dan mess (B-26): maksimal 5 berkas, pemohon + peninjau, terkunci setelah diputuskan.

Matriks: pemohon (member) dan peninjau boleh; orang lain di kantor yang sama 403; kantor lain 404; berkas orang lain
tidak bisa dilampirkan; berkas terlampir bisa dibuka lewat /files/{id}/url hanya oleh yang berhak.
"""
from __future__ import annotations

import io
from collections.abc import Iterator
from datetime import timedelta

import pytest
from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.daily import run_daily_to_ongoing

pytestmark = requires_db

_colour = iter(range(1, 250))
_NO_FILE = "00000000-0000-0000-0000-000000000000"


def _upload(client, world: World, who: str) -> str:
    n = next(_colour)
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (n, 255 - n, (n * 7) % 256)).save(buf, "PNG")
    up = client.post("/files/upload", headers=world.headers(client, who),
                     files={"file": (f"bukti{n}.png", buf.getvalue(), "image/png")})
    assert up.status_code == 200, up.text
    return up.json()["file_id"]


def _day(offset: int) -> str:
    return (jakarta_now().date() + timedelta(days=offset)).isoformat()


@pytest.fixture
def overtime(client, world: World) -> str:
    plan = run_daily_to_ongoing(world)
    sent = client.post("/overtime", headers=world.headers(client, "member"),
                       json={"daily_plan_id": plan, "hours": 2, "reason": "Pengerjaan kabel tambahan"})
    assert sent.status_code == 201, sent.text
    return sent.json()["id"]


@pytest.fixture
def stay(client, world: World) -> Iterator[str]:
    place = client.post("/mess/places", headers=world.headers(client, "hr"), json={
        "mess_name": f"Mess lampiran {world.tag}", "city": "Pekanbaru", "address": "Jl. Uji No. 5", "capacity": 5})
    assert place.status_code == 201, place.text
    mess_id = place.json()["mess_id"]
    sent = client.post("/mess/requests", headers=world.headers(client, "member"), json={
        "mess_id": mess_id, "stay_start_date": _day(1), "stay_end_date": _day(3), "note": "Penugasan proyek"})
    assert sent.status_code == 201, sent.text
    yield sent.json()["mess_stay_id"]
    sync_query("DELETE FROM company_mess_stay WHERE mess_id = %s RETURNING 1", (mess_id,))
    sync_query("DELETE FROM company_mess WHERE mess_id = %s RETURNING 1", (mess_id,))


def _url(kind: str, parent: str, file_id: str | None = None) -> str:
    base = f"/overtime/{parent}/attachments" if kind == "overtime" else f"/mess/{parent}/attachments"
    return f"{base}/{file_id}" if file_id else base


def _decide(client, world: World, kind: str, parent: str) -> None:
    if kind == "overtime":
        res = client.post(f"/overtime/{parent}/review", headers=world.headers(client, "pm"),
                          json={"decision": "APPROVED"})
    else:
        res = client.post(f"/mess/{parent}/decision", headers=world.headers(client, "pm"),
                          json={"approve": True, "note": "ok"})
    assert res.status_code == 200, res.text


@pytest.fixture
def parent_of(request) -> dict[str, str]:
    """Hanya membuat pengajuan jenis yang sedang diuji."""
    kind = request.node.callspec.params["kind"]
    return {kind: request.getfixturevalue("overtime" if kind == "overtime" else "stay")}


KINDS = ["overtime", "mess"]


@pytest.mark.parametrize("kind", KINDS)
def test_role_matrix_on_list_and_add(client, world: World, other_world: World, fake_storage, parent_of, kind):
    parent = parent_of[kind]
    for who in ("member", "pm", "admin"):
        assert client.get(_url(kind, parent), headers=world.headers(client, who)).status_code == 200, who
    assert client.get(_url(kind, parent), headers=world.headers(client, "leader")).status_code == 403
    # kantor lain: keberadaan pengajuan tidak dibocorkan
    assert client.get(_url(kind, parent), headers=other_world.headers(client, "pm")).status_code == 404

    own = _upload(client, world, "member")
    denied = _upload(client, world, "leader")
    assert client.post(_url(kind, parent), headers=world.headers(client, "leader"),
                       json={"file_id": denied}).status_code == 403
    assert client.post(_url(kind, parent), headers=other_world.headers(client, "pm"),
                       json={"file_id": denied}).status_code == 404
    added = client.post(_url(kind, parent), headers=world.headers(client, "member"), json={"file_id": own})
    assert added.status_code == 201, added.text
    assert [a["file_id"] for a in added.json()] == [own] and added.json()[0]["mine"] is True
    # peninjau boleh menambah berkasnya sendiri, dan melihat milik pemohon
    rev = _upload(client, world, "pm")
    both = client.post(_url(kind, parent), headers=world.headers(client, "pm"), json={"file_id": rev})
    assert both.status_code == 201 and len(both.json()) == 2
    assert {a["mine"] for a in both.json()} == {True, False}


@pytest.mark.parametrize("kind", KINDS)
def test_cannot_attach_someone_elses_file(client, world: World, fake_storage, parent_of, kind):
    parent = parent_of[kind]
    foreign = _upload(client, world, "leader")
    res = client.post(_url(kind, parent), headers=world.headers(client, "member"), json={"file_id": foreign})
    assert res.status_code == 404
    missing = client.post(_url(kind, parent), headers=world.headers(client, "member"), json={"file_id": _NO_FILE})
    assert missing.status_code == 404


@pytest.mark.parametrize("kind", KINDS)
def test_max_five_and_duplicate_is_harmless(client, world: World, fake_storage, parent_of, kind):
    parent = parent_of[kind]
    member = world.headers(client, "member")
    ids = [_upload(client, world, "member") for _ in range(6)]
    for fid in ids[:5]:
        assert client.post(_url(kind, parent), headers=member, json={"file_id": fid}).status_code == 201
    again = client.post(_url(kind, parent), headers=member, json={"file_id": ids[0]})
    assert again.status_code == 201 and len(again.json()) == 5
    full = client.post(_url(kind, parent), headers=member, json={"file_id": ids[5]})
    assert full.status_code == 409 and full.json()["error"]["code"] == "LAMPIRAN_PENUH"
    assert len(client.get(_url(kind, parent), headers=member).json()) == 5


@pytest.mark.parametrize("kind", KINDS)
def test_locked_after_decision(client, world: World, fake_storage, parent_of, kind):
    parent = parent_of[kind]
    member = world.headers(client, "member")
    keep, extra = _upload(client, world, "member"), _upload(client, world, "member")
    assert client.post(_url(kind, parent), headers=member, json={"file_id": keep}).status_code == 201
    _decide(client, world, kind, parent)
    locked = client.post(_url(kind, parent), headers=member, json={"file_id": extra})
    assert locked.status_code == 409 and locked.json()["error"]["code"] == "LAMPIRAN_TERKUNCI"
    gone = client.delete(_url(kind, parent, keep), headers=member)
    assert gone.status_code == 409 and gone.json()["error"]["code"] == "LAMPIRAN_TERKUNCI"
    assert client.post(_url(kind, parent), headers=world.headers(client, "pm"),
                       json={"file_id": _upload(client, world, "pm")}).status_code == 409
    # tetap bisa dilihat
    assert [a["file_id"] for a in client.get(_url(kind, parent), headers=member).json()] == [keep]


@pytest.mark.parametrize("kind", KINDS)
def test_file_url_follows_attachment_access(client, world: World, other_world: World, fake_storage, parent_of, kind):
    parent = parent_of[kind]
    fid = _upload(client, world, "member")
    assert client.post(_url(kind, parent), headers=world.headers(client, "member"),
                       json={"file_id": fid}).status_code == 201

    def status(w: World, who: str) -> int:
        return client.get(f"/files/{fid}/url", headers=w.headers(client, who)).status_code

    assert status(world, "member") == 200 and status(world, "pm") == 200 and status(world, "admin") == 200
    assert status(world, "leader") == 404 and status(other_world, "pm") == 404


@pytest.mark.parametrize("kind", KINDS)
def test_delete_by_owner_releases_file(client, world: World, fake_storage, parent_of, kind):
    parent = parent_of[kind]
    member, pm = world.headers(client, "member"), world.headers(client, "pm")
    mine, theirs = _upload(client, world, "member"), _upload(client, world, "pm")
    client.post(_url(kind, parent), headers=member, json={"file_id": mine})
    client.post(_url(kind, parent), headers=pm, json={"file_id": theirs})
    # peninjau hanya menghapus miliknya; pemohon menghapus apa pun
    assert client.delete(_url(kind, parent, mine), headers=pm).status_code == 403
    assert client.delete(_url(kind, parent, _NO_FILE), headers=member).status_code == 404
    left = client.delete(_url(kind, parent, mine), headers=member)
    assert left.status_code == 200 and [a["file_id"] for a in left.json()] == [theirs]
    assert sync_query("SELECT count(*) FROM file_object WHERE id = %s", (mine,))[0][0] == 0
    assert client.delete(_url(kind, parent, theirs), headers=pm).status_code == 200
