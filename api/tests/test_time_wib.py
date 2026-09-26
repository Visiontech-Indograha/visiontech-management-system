from datetime import UTC, datetime

from app.core.time import wib_text


def test_wib_text_converts_utc_to_wib_for_documents() -> None:
    assert wib_text(datetime(2026, 9, 26, 10, 41, 5, tzinfo=UTC)) == "26-09-2026 17:41 WIB"
    assert wib_text("2026-09-26T20:00:00+00:00") == "27-09-2026 03:00 WIB"
    assert wib_text(datetime(2026, 9, 26, 10, 41)) == "26-09-2026 17:41 WIB"
    assert wib_text(None) == ""
