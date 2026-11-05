"""
Popup K3 wajib baca memakai peran efektif (ADR 0002): peran tambahan ikut melihat kampanye K3 untuk perannya.
Flag mati = hanya peran utama (persis lama). Satu kali konfirmasi per kampanye, tidak ganda lintas peran.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

import pytest

from app.core.config import settings
from app.core.time import jakarta_now
from tests.conftest import World, db_exclusive, requires_db, sync_query

pytestmark = requires_db

HR = "ADMIN_HR_GA"


@pytest.fixture
def k3_world(world: World) -> Iterator[World]:
    # Popup K3 memilih kampanye aktif GLOBAL: tes diserialkan lintas worker xdist.
    with db_exclusive(727302):
        world.add_person("hse", "HSE")
        yield world


def _campaign(client, world: World, audience: str, title: str) -> str:
    today = jakarta_now().date()
    r = client.post("/hse/campaigns", headers=world.headers(client, "hse"), json={
        "title": title, "summary": "Ringkasan uji", "content_html": "<p>Isi uji K3</p>",
        "target_audience": audience, "is_mandatory": True, "cooldown_seconds": 3,
        "start_date": today.isoformat(), "end_date": (today + timedelta(days=3)).isoformat(), "is_active": True})
    assert r.status_code == 201, r.text
    return r.json()["campaign_id"]


def _popup(client, world: World, who: str) -> str | None:
    r = client.get("/hse/campaigns/active-popup", headers=world.headers(client, who))
    assert r.status_code == 200, r.text
    campaign = r.json()["campaign"]
    return campaign["campaign_id"] if campaign else None


def _ack(client, world: World, who: str, campaign_id: str) -> None:
    r = client.post(f"/hse/campaigns/{campaign_id}/acknowledge", headers=world.headers(client, who), json={
        "platform": "web", "device_info": "uji", "scroll_completed": True, "read_duration_seconds": 10})
    assert r.status_code == 200, r.text


def _assign(client, world: World, who: str, role: str) -> None:
    office = None if role == "OPERATIONAL_MANAGER" else world.org_id
    r = client.post(f"/users/{world.users[who]}/role-assignments", headers=world.headers(client, "admin"),
                    json={"role": role, "office_id": office})
    assert r.status_code == 201, r.text


def _cleanup(*ids: str) -> None:
    for cid in ids:
        sync_query("DELETE FROM hse_campaign_acknowledgments WHERE campaign_id = %s;", (cid,))
        sync_query("DELETE FROM hse_campaigns WHERE campaign_id = %s;", (cid,))


def _seen(client, world: World, who: str) -> set[str]:
    """Konfirmasi popup satu per satu sampai habis; kembalikan kampanye yang tampil."""
    seen: list[str] = []
    for _ in range(5):
        cid = _popup(client, world, who)
        if cid is None:
            break
        seen.append(cid)
        _ack(client, world, who, cid)
    assert len(seen) == len(set(seen)), "kampanye yang sama tampil dua kali"
    return set(seen)


def test_flag_off_primary_role_only(client, k3_world: World, monkeypatch):
    """Paritas: flag mati, karyawan lapangan dengan penugasan HR tetap hanya melihat kampanye FIELD."""
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)
    field = _campaign(client, k3_world, "FIELD", "K3 lapangan")
    office = _campaign(client, k3_world, "OFFICE", "K3 kantor")
    try:
        assert _seen(client, k3_world, "member") >= {field}
        assert office not in _seen(client, k3_world, "member")
    finally:
        _cleanup(field, office)


def test_flag_on_additional_role_sees_both_audiences_once(client, k3_world: World, monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    _assign(client, k3_world, "member", HR)
    field = _campaign(client, k3_world, "FIELD", "K3 lapangan")
    office = _campaign(client, k3_world, "OFFICE", "K3 kantor")
    try:
        seen = _seen(client, k3_world, "member")
        assert {field, office} <= seen
        assert _popup(client, k3_world, "member") is None  # sudah ditutup satu kali per kampanye
        n = sync_query("SELECT count(*) FROM hse_campaign_acknowledgments WHERE campaign_id IN (%s, %s) "
                       "AND user_id = %s;", (field, office, k3_world.users["member"]))[0][0]
        assert n == 2
    finally:
        _cleanup(field, office)


def test_flag_on_hr_plus_om_sees_office_campaign_once(client, k3_world: World, monkeypatch):
    """HR yang juga OM: kampanye kantor tampil sekali (bukan satu per peran) dan tidak ganda setelah ditutup."""
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    _assign(client, k3_world, "hr", "OPERATIONAL_MANAGER")
    office = _campaign(client, k3_world, "OFFICE", "K3 kantor")
    field = _campaign(client, k3_world, "FIELD", "K3 lapangan")
    try:
        assert _popup(client, k3_world, "hr") == office
        _ack(client, k3_world, "hr", office)
        assert _popup(client, k3_world, "hr") is None  # peran kantor tidak melihat kampanye FIELD
    finally:
        _cleanup(office, field)
