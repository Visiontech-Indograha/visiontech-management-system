"""Kursor keyset: pengemasan, validasi (422), dan pemotongan halaman. Tanpa DB."""
from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response

from app.core.keyset import NEXT_CURSOR_HEADER, decode_cursor, encode_cursor, finish_page, parse_cursor


def test_roundtrip_datetime_uuid():
    at, ident = datetime(2026, 11, 5, 1, 2, 3, 456789, tzinfo=UTC), uuid4()
    got = decode_cursor(encode_cursor((at, ident)), ("datetime", "uuid"))
    assert got == (at, ident)


def test_roundtrip_date_datetime_uuid():
    parts = (date(2026, 11, 5), datetime(2026, 11, 5, 8, 0, tzinfo=UTC), uuid4())
    assert decode_cursor(encode_cursor(parts), ("date", "datetime", "uuid")) == parts


def test_parse_modes():
    assert parse_cursor(None, ("uuid",)) is None  # mode lama
    assert parse_cursor("", ("uuid",)) == ()  # halaman pertama keyset


@pytest.mark.parametrize("raw", ["bukan-base64!!", "e30", "W10", "WyJ4Il0", "x" * 301])
def test_bad_cursor_is_422(raw: str):
    with pytest.raises(HTTPException) as exc:
        decode_cursor(raw, ("datetime", "uuid"))
    assert exc.value.status_code == 422 and "Kursor" in str(exc.value.detail)


def test_wrong_types_and_naive_datetime_rejected():
    naive = encode_cursor(("2026-11-05T01:02:03", str(uuid4())))
    for raw in (naive, encode_cursor(("2026-11-05T01:02:03+00:00", "bukan-uuid")),
                encode_cursor(("2026-11-05T01:02:03+00:00",))):
        with pytest.raises(HTTPException):
            decode_cursor(raw, ("datetime", "uuid"))


def test_finish_page_sets_header_only_when_more():
    r = Response()
    assert finish_page([1, 2, 3], 2, r, lambda x: (str(x),)) == [1, 2]
    assert NEXT_CURSOR_HEADER in r.headers
    r2 = Response()
    assert finish_page([1, 2], 2, r2, lambda x: (str(x),)) == [1, 2]
    assert NEXT_CURSOR_HEADER not in r2.headers
