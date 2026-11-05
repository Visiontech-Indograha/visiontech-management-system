"""
app/core/keyset.py

Paginasi keyset (kursor) bersama: parameter opsional `cursor`, header `X-Next-Cursor`.

Kontrak:
- Tanpa `cursor` (parameter tidak ada) = perilaku lama persis (mode `page`/`size`, `X-Total-Count`/`total`).
- `cursor` ada (boleh kosong `?cursor=` = halaman pertama) = mode keyset: ambil `size+1` baris, kirim
  `X-Next-Cursor` bila masih ada halaman berikut, TANPA hitung total (mahal) dan tanpa OFFSET.
- Kursor opak (base64url JSON). Nilainya tidak dipercaya: diurai dan divalidasi tipenya; rusak -> 422.
"""
from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Callable, Sequence
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, Query, Response

NEXT_CURSOR_HEADER = "X-Next-Cursor"
MAX_CURSOR_LENGTH = 300
CURSOR_ERROR = "Kursor halaman tidak valid. Muat ulang daftar dari awal."

Kind = Literal["datetime", "date", "uuid"]


def cursor_query() -> Any:
    """Definisi query `cursor` seragam (batas panjang sama di semua daftar)."""
    return Query(
        None,
        max_length=MAX_CURSOR_LENGTH,
        description="Kursor keyset (opak). Kosong = halaman pertama mode keyset; tidak ada = mode page/size lama.",
    )


def encode_cursor(parts: Sequence[datetime | date | UUID | str]) -> str:
    """Kemas nilai kunci urut baris terakhir menjadi string opak."""
    values = [p.isoformat() if isinstance(p, (datetime, date)) else str(p) for p in parts]
    raw = json.dumps(values, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _bad() -> HTTPException:
    return HTTPException(status_code=422, detail=CURSOR_ERROR)


def decode_cursor(raw: str, kinds: Sequence[Kind]) -> tuple[Any, ...]:
    """Urai kursor; tolak (422) bila bukan base64/JSON, jumlah, atau tipe nilai salah."""
    if len(raw) > MAX_CURSOR_LENGTH:
        raise _bad()
    try:
        data = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    except (binascii.Error, ValueError):
        raise _bad() from None
    if not isinstance(data, list) or len(data) != len(kinds) or not all(isinstance(v, str) for v in data):
        raise _bad()
    out: list[Any] = []
    try:
        for value, kind in zip(data, kinds, strict=True):
            if kind == "datetime":
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    raise ValueError("tanpa zona waktu")
                out.append(parsed)
            elif kind == "date":
                out.append(date.fromisoformat(value))
            else:
                out.append(UUID(value))
    except ValueError:
        raise _bad() from None
    return tuple(out)


def parse_cursor(raw: str | None, kinds: Sequence[Kind]) -> tuple[Any, ...] | None:
    """None = mode lama; "" = halaman pertama keyset (hasil `()`); selain itu kursor terurai."""
    if raw is None:
        return None
    if raw == "":
        return ()
    return decode_cursor(raw, kinds)


def finish_page[T](
    rows: Sequence[T], size: int, response: Response, make_cursor: Callable[[T], Sequence[Any]]
) -> list[T]:
    """Dari `size+1` baris: potong ke `size` dan isi `X-Next-Cursor` bila masih ada sisa."""
    page = list(rows[:size])
    if len(rows) > size and page:
        response.headers[NEXT_CURSOR_HEADER] = encode_cursor(make_cursor(page[-1]))
    return page
