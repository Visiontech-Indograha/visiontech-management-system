"""Validasi input: unggahan palsu ditolak dari isinya, dan field teks/kredensial dibatasi panjangnya."""
from __future__ import annotations

from tests.conftest import WORLD_PASSWORD, World, requires_db

pytestmark = requires_db


def test_upload_with_forged_content_type_is_rejected(client, world: World) -> None:
    response = client.post(
        "/files/upload",
        headers=world.headers(client, "member"),
        files={"file": ("laporan.pdf", b"<script>alert(1)</script>", "application/pdf")},
    )
    assert response.status_code == 415, response.text


def test_login_rejects_oversized_credentials(client, world: World) -> None:
    too_long = client.post("/auth/login", json={"email": "a" * 300 + "@x.id", "password": WORLD_PASSWORD})
    assert too_long.status_code == 422
    huge_password = client.post("/auth/login", json={"email": world.logins["member"], "password": "x" * 5000})
    assert huge_password.status_code == 422


def test_overtime_reason_is_length_limited(client, world: World) -> None:
    response = client.post(
        "/overtime",
        headers=world.headers(client, "member"),
        json={"daily_plan_id": "00000000-0000-0000-0000-000000000000", "hours": 2, "reason": "a" * 1001},
    )
    assert response.status_code == 422


def test_like_wildcards_in_search_terms_are_escaped() -> None:
    from app.core.repository import escape_like

    bs = chr(92)
    assert escape_like("100%_a" + bs + "b") == "100" + bs + "%" + bs + "_a" + bs + bs + "b"
    assert escape_like(None) is None


def test_dynamic_update_rejects_non_identifier_column_names() -> None:
    import pytest

    from app.core.repository import safe_columns

    assert safe_columns(["name", "update_at"]) == ["name", "update_at"]
    with pytest.raises(ValueError):
        safe_columns(["name = 'x'; DROP TABLE users; --"])


def test_date_ranges_reject_end_before_start():
    import pytest
    from pydantic import ValidationError

    from app.modules.exports.schemas.export_schema import PeriodicExportRequest
    from app.modules.leaves.schemas.leave_schema import LeaveCreate

    with pytest.raises(ValidationError, match="Tanggal selesai"):
        LeaveCreate(leave_type="ANNUAL", start_date="2026-11-10", end_date="2026-11-01", reason="Keperluan")
    with pytest.raises(ValidationError, match="Tanggal selesai"):
        PeriodicExportRequest(division_id="11111111-1111-4111-8111-111111111111",
                              start_date="2026-11-10", end_date="2026-11-01")
