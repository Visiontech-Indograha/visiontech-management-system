"""
app/core/list_params.py

Parameter daftar bersama: pencarian teks (`q`) dan paginasi opsional (`page`/`size`) + header `X-Total-Count`.
Tanpa parameter perilaku lama tetap (semua baris), sehingga klien lama tidak terpengaruh.
"""
from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable, Sequence
from datetime import date
from typing import Any

from fastapi import HTTPException, Query, Response

MAX_PAGE_SIZE = 100
TOTAL_HEADER = "X-Total-Count"


def check_date_range(
    start: date | None, end: date | None, *, start_name: str = "date_from", end_name: str = "date_to"
) -> None:
    """Tolak rentang tanggal terbalik (mulai setelah akhir) dengan 422."""
    if start and end and start > end:
        raise HTTPException(status_code=422, detail=f"{start_name} tidak boleh setelah {end_name}")


class ListParams:
    """Dependency FastAPI: `?q=&page=&size=`. Salah satu `page`/`size` mengaktifkan paginasi (size bawaan 20)."""

    def __init__(
        self,
        q: str | None = Query(None, max_length=100, description="Kata kunci pencarian (tanpa beda huruf besar/kecil)"),
        page: int | None = Query(None, ge=1, le=100000, description="Nomor halaman, mulai dari 1"),
        size: int | None = Query(None, ge=1, le=MAX_PAGE_SIZE, description="Jumlah baris per halaman (maks 100)"),
    ) -> None:
        self.q = (q or "").strip() or None
        self.paged = page is not None or size is not None
        self.page = page or 1
        self.size = size or 20


def _fold(value: Any) -> str:
    """Huruf kecil tanpa aksen supaya pencarian toleran."""
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return "".join(c for c in text if not unicodedata.combining(c))


def apply_list[T](
    items: Iterable[T],
    params: ListParams,
    response: Response,
    haystack: Callable[[T], Iterable[Any]],
    *,
    extra: Callable[[T], bool] | None = None,
) -> Sequence[T]:
    """Saring (`q` + `extra`), potong halaman bila diminta, dan isi `X-Total-Count` (jumlah setelah filter)."""
    rows = list(items)
    if extra is not None:
        rows = [r for r in rows if extra(r)]
    if params.q:
        needle = _fold(params.q)
        rows = [r for r in rows if any(needle in _fold(v) for v in haystack(r))]
    response.headers[TOTAL_HEADER] = str(len(rows))
    if params.paged:
        start = (params.page - 1) * params.size
        rows = rows[start : start + params.size]
    return rows
