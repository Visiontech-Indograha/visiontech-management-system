"""
R-28 M0 · Snapshot OpenAPI: pemindahan folder (docs/26 M1–M8) tidak boleh mengubah API.

Membandingkan `app.openapi()` dengan `tests/snapshots/openapi.json` (rute, metode, skema, status).
Perubahan API yang DISENGAJA: perbarui snapshot dengan
`UPDATE_OPENAPI_SNAPSHOT=1 pytest tests/test_openapi_snapshot.py`, lalu tinjau diff-nya di commit.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.main import app

SNAPSHOT = Path(__file__).resolve().parents[1] / "snapshots" / "openapi.json"


def _current() -> str:
    return json.dumps(app.openapi(), indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def test_openapi_matches_snapshot():
    current = _current()
    if os.environ.get("UPDATE_OPENAPI_SNAPSHOT") == "1" or not SNAPSHOT.exists():
        SNAPSHOT.write_text(current, encoding="utf-8", newline="\n")
    expected = SNAPSHOT.read_text(encoding="utf-8")
    assert current == expected, (
        "OpenAPI berubah dari snapshot. Bila disengaja: UPDATE_OPENAPI_SNAPSHOT=1 lalu tinjau diff."
    )
