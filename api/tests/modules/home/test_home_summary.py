"""Ringkasan Beranda: angka per peran, tanpa bocor ke peran yang tidak berwenang."""
from __future__ import annotations

from tests.conftest import World, requires_db

pytestmark = requires_db

_FIELDS = (
    "leaves_to_review", "attendance_to_review", "overtime_to_review", "mess_to_review",
    "loan_requests_to_review", "corrections_to_review", "offboarding_open",
)


def _summary(client, world: World, who: str) -> dict:
    response = client.get("/home/summary", headers=world.headers(client, who))
    assert response.status_code == 200, response.text
    return response.json()


def test_every_role_gets_consistent_non_negative_counts(client, world: World) -> None:
    for who in ("admin", "hr", "pm", "ops", "leader", "member"):
        data = _summary(client, world, who)
        keys = (*_FIELDS, "my_leaves_pending", "notifications_unread")
        assert all(isinstance(data[k], int) and data[k] >= 0 for k in keys)
        assert data["total_to_review"] == sum(data[k] for k in _FIELDS), who


def test_field_member_has_nothing_to_review(client, world: World) -> None:
    data = _summary(client, world, "member")
    assert all(data[k] == 0 for k in _FIELDS)


def test_requires_login(client) -> None:
    assert client.get("/home/summary").status_code == 401
