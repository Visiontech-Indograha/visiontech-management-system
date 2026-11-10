"""
UU PDP: hapus permanen karyawan harus ikut menghapus SEMUA berkas pribadinya di penyimpanan objek
(foto + varian, dokumen KTP/SIM, swafoto absensi) dan mengosongkan embedding wajah.
Penggantian foto dan hapus dokumen juga tidak boleh meninggalkan varian yatim.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.core.file_cleanup import object_variants, purge_keys
from tests.conftest import World, requires_db, sync_query
from tests.modules.attendance.test_attendance_channel import _check_in, _storage  # noqa: F401

pytestmark = requires_db


def _upload(client, world: World, who: str, color: int, as_user: str | None = None) -> tuple[str, str]:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (color, 20, 30)).save(buf, "PNG")
    res = client.post("/files/upload", headers=world.headers(client, as_user or who),
                      files={"file": ("f.png", buf.getvalue(), "image/png")})
    assert res.status_code in (200, 201), res.text
    file_id = res.json()["file_id"]
    return file_id, sync_query("SELECT storage_key FROM file_object WHERE id = %s", (file_id,))[0][0]


def _alive(stored: dict, key: str) -> list[str]:
    return [n for n in object_variants(key) if n in stored]


def test_object_variants_cover_original_and_webp():
    assert object_variants("o/abc.png") == ["o/abc.png", "o/abc_full.webp", "o/abc_view.webp", "o/abc_thumb.webp"]
    assert object_variants("o/abc_view.webp")[0] == "o/abc_view.webp"
    assert "o/abc_thumb.webp" in object_variants("o/abc_view.webp")


@pytest.mark.usefixtures("_storage")
def test_hapus_permanen_menghapus_semua_berkas_dan_varian(client, world, fake_storage):
    emp = world.employees["member"]
    _, photo = _upload(client, world, "member", 11)
    _, ktp = _upload(client, world, "hr", 12)
    sync_query("UPDATE employee SET photo_path = %s, profile_photo_path = %s, face_embedding = '[0.1, 0.2]'::jsonb "
               "WHERE employee_id = %s RETURNING 1", (photo, photo, emp))
    sync_query("INSERT INTO employee_file (employee_id, type, path_file, active_at) VALUES (%s, 'KTP', %s, now()) "
               "RETURNING 1", (emp, ktp))
    checked = _check_in(client, world, "member", "MOBILE")
    assert checked.status_code == 200, checked.text
    selfie = sync_query("SELECT face_photo_path FROM attendance WHERE employee_id = %s", (emp,))[0][0]
    assert all(_alive(fake_storage, k) for k in (photo, ktp, selfie))

    sync_query("UPDATE employee SET offboarding_status = 'offboarded' WHERE employee_id = %s RETURNING 1", (emp,))
    assert client.post(f"/employees/{emp}/archive", headers=world.headers(client, "hr"), json={}).status_code == 200
    done = client.delete(f"/employees/{emp}", headers=world.headers(client, "admin"))
    assert done.status_code == 200, done.text

    for key in (photo, ktp, selfie):
        assert _alive(fake_storage, key) == [], "varian berkas pribadi masih tersisa di penyimpanan"
        assert sync_query("SELECT count(*) FROM file_object WHERE storage_key = %s", (key,))[0][0] == 0


@pytest.mark.usefixtures("_storage")
def test_ganti_foto_menghapus_foto_lama(client, world, fake_storage):
    emp = world.employees["member"]
    old_id, old_key = _upload(client, world, "member", 21)
    new_id, new_key = _upload(client, world, "member", 22)
    own = client.put("/employees/me/photo", headers=world.headers(client, "member"), json={"file_id": old_id})
    assert own.status_code == 200, own.text
    again = client.put("/employees/me/photo", headers=world.headers(client, "member"), json={"file_id": new_id})
    assert again.status_code == 200, again.text
    assert _alive(fake_storage, old_key) == []
    assert _alive(fake_storage, new_key) != []
    assert sync_query("SELECT photo_path FROM employee WHERE employee_id = %s", (emp,))[0][0] == new_key


def test_purge_keys_idempoten(fake_storage):
    fake_storage["o/x_full.webp"] = b"1"
    assert purge_keys(["o/x.png"]) == (4, 0)
    assert purge_keys(["o/x.png"]) == (4, 0)
    assert "o/x_full.webp" not in fake_storage


@pytest.mark.anyio
async def test_skrip_operator_yatim_cek_lalu_hapus(world, fake_storage, monkeypatch, capsys):
    import importlib.util
    from pathlib import Path

    from app.core import storage

    spec = importlib.util.spec_from_file_location(
        "bersihkan_berkas_yatim", Path(__file__).resolve().parents[3] / "scripts" / "bersihkan_berkas_yatim.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    org = world.employees["member"]  # uuid valid apa pun sebagai awalan
    ghost = f"{org}/aaaaaaaa-0000-0000-0000-bbbbbbbbbbbb"
    for suffix in (".png", "_full.webp", "_thumb.webp"):
        fake_storage[ghost + suffix] = b"x"
    monkeypatch.setattr(storage, "list_object_keys", lambda: list(fake_storage))

    assert await mod.main(hapus=False) == 0
    assert "tidak ada yang diubah" in capsys.readouterr().out
    assert len(fake_storage) == 3
    assert await mod.main(hapus=True) == 0
    assert fake_storage == {}
    assert await mod.main(hapus=True) == 0  # idempoten
