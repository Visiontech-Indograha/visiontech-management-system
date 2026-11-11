"""
Foto titik survei WO (work_order_survey_points.photos_json) lewat GET /files/{id}/url.
Matriks peran: tim WO (ketua/anggota), PM pengelola, OM, SA boleh; tim lain, karyawan tanpa tim, PM divisi lain,
HR/GA mendapat 404 (BOLA/IDOR). Mencakup bentuk {file_id} dan bentuk lama (larik id).
"""
from __future__ import annotations

import hashlib
import json
import uuid

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.orders import make_client

pytestmark = requires_db


def _file(w: World) -> str:
    key = f"uji-titik/{uuid.uuid4().hex}.jpg"
    return str(sync_query(
        "INSERT INTO file_object (office_id, storage_key, file_name, mime_type, byte_size, sha256) "
        "VALUES (%s, %s, 'foto.jpg', 'image/jpeg', 10, decode(%s, 'hex')) RETURNING id::text",
        (w.org_id, key, hashlib.sha256(key.encode()).hexdigest()))[0][0])


def _wo_with_point(w: World, photos: list) -> None:
    tag = uuid.uuid4().hex[:8]
    wo = sync_query(
        "INSERT INTO client_work_orders (wo_number, client_id, division_id, pm_id, lead_team_id, title, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, 'SURVEY_IN_PROGRESS') RETURNING work_order_id",
        (f"FT-{tag}", make_client(), w.unit_id, w.employees["pm"], w.team_id, f"WO foto {tag}"))[0][0]
    sync_query(
        "INSERT INTO work_order_survey_points (work_order_id, point_name, photos_json) "
        "VALUES (%s, 'Titik 1', CAST(%s AS jsonb))", (wo, json.dumps(photos)))


def _setup(w: World) -> None:
    unit2 = w.add_unit("Dua")
    pm2 = w.add_person("pm2", "PM", unit_id=unit2)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (pm2, unit2))
    rival = w.add_person("rival", None)
    team2 = sync_query(
        "INSERT INTO team (office_id, division_id, leader_employee_id, name) VALUES (%s, %s, %s, 'Tim lain') "
        "RETURNING team_id", (w.org_id, w.unit_id, rival))[0][0]
    sync_query("INSERT INTO member (team_id, employee_id) VALUES (%s, %s)", (team2, rival))
    w.add_person("outsider", None)


@pytest.mark.parametrize("legacy", [False, True])
def test_survey_point_photo_access_matrix(client, world: World, legacy: bool):
    _setup(world)
    fid = _file(world)
    _wo_with_point(world, [fid] if legacy else [{"file_id": fid, "requirement_id": None}])
    for who in ("leader", "member", "pm", "ops", "admin"):
        res = client.get(f"/files/{fid}/url", headers=world.headers(client, who))
        assert res.status_code == 200, (who, res.text)
    for who in ("rival", "outsider", "pm2", "hr"):
        res = client.get(f"/files/{fid}/url", headers=world.headers(client, who))
        assert res.status_code == 404, (who, res.text)


def test_unrelated_file_stays_hidden(client, world: World):
    _setup(world)
    fid = _file(world)
    _wo_with_point(world, [{"file_id": _file(world)}])
    assert client.get(f"/files/{fid}/url", headers=world.headers(client, "leader")).status_code == 404
