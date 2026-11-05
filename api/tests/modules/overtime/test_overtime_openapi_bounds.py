"""Batas jam lembur tampil di OpenAPI (tanpa DB) dan sama dengan aturan OvertimeService (0 < jam <= 12)."""
from __future__ import annotations

from app.main import app


def test_hours_bounds_in_openapi() -> None:
    hours = app.openapi()["components"]["schemas"]["OvertimeCreate"]["properties"]["hours"]
    assert hours["exclusiveMinimum"] == 0
    assert hours["maximum"] == 12
