"""
api/tests/modules/hse/test_hse_carousel.py

Kampanye K3 bergambar banyak (carousel): daftar foto `media_paths` dan aturan durasi baca.
1. Foto diunggah lewat /files/upload, lalu dipasang ke kampanye oleh HSE.
2. Popup untuk pengguna biasa memuat urutan foto yang sama.
3. Foto kampanye aktif bisa dibuka pengguna lain lewat pemeriksaan akses yang sama (bukan jalur baru).
4. Aturan ditolak: durasi di luar 10-300 dtk, kurang dari 3 dtk per foto, lebih dari 8 foto,
   berkas milik orang lain, dan format selain JPG/PNG/WebP.
"""
from __future__ import annotations

import io
from datetime import timedelta

import pytest
from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import World, requires_db

pytestmark = requires_db


def _png(color: tuple[int, int, int], size: tuple[int, int] = (120, 80)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _upload(client, headers: dict[str, str], name: str, data: bytes, mime: str) -> str:
    res = client.post("/files/upload", headers=headers, files={"file": (name, data, mime)})
    assert res.status_code == 200, res.text
    return res.json()["file_id"]


def _campaign_payload(media: list[str], cooldown: int) -> dict:
    today = jakarta_now().date()
    return {
        "title": "Carousel K3 uji",
        "content_html": "<p>Materi keselamatan kerja.</p>",
        "target_audience": "ALL",
        "is_mandatory": True,
        "cooldown_seconds": cooldown,
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=5)).isoformat(),
        "media_paths": media,
    }


@pytest.fixture
def hse_world(client, world: World) -> World:
    world.add_person("hse", "HSE")
    return world


@pytest.fixture
def photos(client, hse_world: World, fake_storage) -> list[str]:
    headers = hse_world.headers(client, "hse")
    return [
        _upload(client, headers, f"k3-{i}.png", _png((40 * i, 90, 160)), "image/png")
        for i in range(1, 4)
    ]


def test_carousel_campaign_is_saved_and_served_in_popup(client, hse_world: World, photos: list[str]):
    created = client.post(
        "/hse/campaigns",
        headers=hse_world.headers(client, "hse"),
        json=_campaign_payload(photos, cooldown=10),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["media_paths"] == photos
    # Kolom lama tetap terisi (foto pertama) untuk klien yang belum memakai daftar foto.
    assert body["media_path"] == photos[0]

    popup = client.get("/hse/campaigns/active-popup", headers=hse_world.headers(client, "member"))
    assert popup.status_code == 200
    assert popup.json()["campaign"]["media_paths"] == photos

    # Foto kampanye aktif terlihat pengguna lain lewat pemeriksaan akses berkas yang sama.
    url = client.get(f"/files/{photos[1]}/url", headers=hse_world.headers(client, "member"))
    assert url.status_code == 200, url.text


def test_carousel_rejects_duration_outside_rules(client, hse_world: World, photos: list[str]):
    headers = hse_world.headers(client, "hse")
    too_short = client.post("/hse/campaigns", headers=headers, json=_campaign_payload(photos, cooldown=5))
    assert too_short.status_code == 422
    assert too_short.json()["error"]["code"] == "VALIDATION_ERROR"

    # 3 foto x 3 dtk = minimal 9 dtk, tetapi aturan 10-300 tetap berlaku.
    single = client.post("/hse/campaigns", headers=headers, json=_campaign_payload(photos[:1], cooldown=9))
    assert single.status_code == 422

    too_many = client.post(
        "/hse/campaigns", headers=headers, json=_campaign_payload(photos + photos[:1] * 6, cooldown=300)
    )
    assert too_many.status_code == 422


def test_carousel_rejects_foreign_or_non_photo_files(client, hse_world: World, photos: list[str], fake_storage):
    member_headers = hse_world.headers(client, "member")
    foreign = _upload(client, member_headers, "milik-member.png", _png((1, 2, 3)), "image/png")
    headers = hse_world.headers(client, "hse")

    res = client.post("/hse/campaigns", headers=headers, json=_campaign_payload([foreign], cooldown=10))
    assert res.status_code == 422

    pdf = _upload(client, headers, "panduan.pdf", b"%PDF-1.4 panduan K3 uji", "application/pdf")
    res = client.post("/hse/campaigns", headers=headers, json=_campaign_payload([pdf], cooldown=10))
    assert res.status_code == 422


def test_carousel_update_keeps_rules_and_allows_reorder(client, hse_world: World, photos: list[str]):
    headers = hse_world.headers(client, "hse")
    created = client.post("/hse/campaigns", headers=headers, json=_campaign_payload(photos, cooldown=12))
    campaign_id = created.json()["campaign_id"]

    reordered = client.put(
        f"/hse/campaigns/{campaign_id}",
        headers=headers,
        json={"media_paths": list(reversed(photos))},
    )
    assert reordered.status_code == 200, reordered.text
    assert reordered.json()["media_paths"] == list(reversed(photos))

    # Menurunkan durasi di bawah 3 dtk per foto ditolak.
    short = client.put(f"/hse/campaigns/{campaign_id}", headers=headers, json={"cooldown_seconds": 8})
    assert short.status_code == 422


def test_popup_stays_until_acknowledged_and_read_recorded_once(client, hse_world: World, photos: list[str]):
    hse = hse_world.headers(client, "hse")
    member = hse_world.headers(client, "member")
    created = client.post("/hse/campaigns", headers=hse, json=_campaign_payload([], cooldown=5))
    assert created.status_code == 201, created.text
    campaign_id = created.json()["campaign_id"]

    # Memuat ulang sebelum konfirmasi tetap memunculkan popup (baca wajib tidak bisa dilewati).
    for _ in range(2):
        shown = client.get("/hse/campaigns/active-popup", headers=member)
        assert shown.json()["campaign"]["campaign_id"] == campaign_id

    ack_url = f"/hse/campaigns/{campaign_id}/acknowledge"
    first_read = client.post(ack_url, headers=member, json={"read_duration_seconds": 12})
    assert first_read.status_code == 200, first_read.text
    second_read = client.post(ack_url, headers=member, json={"read_duration_seconds": 40})
    assert second_read.status_code == 200, second_read.text
    readers = client.get(f"/hse/campaigns/{campaign_id}/readers", headers=hse).json()["readers"]
    assert len(readers) == 1
    assert readers[0]["read_duration_seconds"] == 12


def test_captions_round_trip_and_rules(client, hse_world: World, photos: list[str]):
    headers = hse_world.headers(client, "hse")
    captions = ["Pakai helm.", "Pakai harness", "Jaga jarak"]
    payload = _campaign_payload(photos, cooldown=12)
    payload["media_captions"] = captions
    created = client.post("/hse/campaigns", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["media_captions"] == captions

    popup = client.get("/hse/campaigns/active-popup", headers=hse_world.headers(client, "member"))
    assert popup.json()["campaign"]["media_captions"] == captions

    # Jumlah keterangan harus sama dengan jumlah foto.
    mismatch = dict(payload, media_captions=["satu"])
    assert client.post("/hse/campaigns", headers=headers, json=mismatch).status_code == 422
    # Maks 300 karakter per keterangan.
    long_text = dict(payload, media_captions=["x" * 301, "y", "z"])
    assert client.post("/hse/campaigns", headers=headers, json=long_text).status_code == 422
