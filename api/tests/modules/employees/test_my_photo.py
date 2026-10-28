"""
Foto profil: karyawan mengganti fotonya sendiri; /auth/me mengembalikan id berkas (bukan storage_key); foto orang
tampil di daftar (cuti, tim, mess); berkas orang lain tidak bisa dijadikan foto sendiri.
"""
from __future__ import annotations

import io

from PIL import Image

from tests.conftest import World, requires_db

pytestmark = requires_db


def _upload(client, world: World, who: str, colour=(10, 120, 200)) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), colour).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("foto.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def test_employee_sets_own_photo_and_me_returns_a_file_id(client, world: World, fake_storage):
    file_id = _upload(client, world, "member")
    changed = client.put("/employees/me/photo", headers=world.headers(client, "member"), json={"file_id": file_id})
    assert changed.status_code == 200, changed.text
    assert changed.json()["photo_file_id"] == file_id

    me = client.get("/auth/me", headers=world.headers(client, "member")).json()
    assert me["photo_file_id"] == file_id  # id berkas, bukan storage_key

    # rekan satu kantor boleh melihat foto profil (izin dasar view:users) → URL berkas terbit
    assert client.get(f"/files/{file_id}/url", headers=world.headers(client, "leader")).status_code == 200


def test_cannot_use_someone_elses_upload_as_own_photo(client, world: World, fake_storage):
    others = _upload(client, world, "leader")
    denied = client.put("/employees/me/photo", headers=world.headers(client, "member"), json={"file_id": others})
    assert denied.status_code == 422


def test_photo_can_be_removed(client, world: World, fake_storage):
    file_id = _upload(client, world, "member")
    headers = world.headers(client, "member")
    client.put("/employees/me/photo", headers=headers, json={"file_id": file_id})
    removed = client.put("/employees/me/photo", headers=headers, json={"file_id": None})
    assert removed.status_code == 200 and removed.json()["photo_file_id"] is None
    assert client.get("/auth/me", headers=headers).json()["photo_file_id"] is None


def test_hr_and_admin_can_still_change_other_peoples_photo(client, world: World, fake_storage):
    file_id = _upload(client, world, "hr")
    for who in ("hr", "admin"):
        changed = client.put(f"/employees/{world.employees['member']}", headers=world.headers(client, who),
                             json={"photo_file_id": file_id})
        assert changed.status_code == 200, (who, changed.text)
        assert changed.json()["photo_file_id"] == file_id


def test_team_members_carry_the_photo_id(client, world: World, fake_storage):
    file_id = _upload(client, world, "member")
    client.put("/employees/me/photo", headers=world.headers(client, "member"), json={"file_id": file_id})
    team = client.get(f"/teams/{world.team_id}", headers=world.headers(client, "pm")).json()
    mine = [m for m in team["members"] if m["employee_id"] == world.employees["member"]]
    assert mine and mine[0]["photo_file_id"] == file_id
