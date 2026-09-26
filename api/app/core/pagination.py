"""
app/core/pagination.py
Cursor pagination standar VMS.
Semua endpoint list menggunakan format ini — tidak ada offset/page.

Contoh request:  GET /employees?limit=20&cursor=eyJ...&sort=created_at:desc
Contoh response: { "items": [...], "next_cursor": "eyJ...", "has_more": true }
"""
from __future__ import annotations

import base64
import json
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None  # opsional, mahal untuk dihitung selalu


def encode_cursor(data: dict[str, Any]) -> str:
    """Encode dict menjadi string cursor yang aman untuk URL."""
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode cursor kembali ke dict. Lempar ValueError bila rusak."""
    try:
        data: dict[str, Any] = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return data
    except Exception as exc:
        raise ValueError("Cursor tidak valid.") from exc


def parse_sort(sort_param: str, allowed: set[str]) -> tuple[str, str]:
    """
    Parse parameter sort seperti 'created_at:desc'.
    Kembalikan (field, direction).
    Lempar ValueError jika field tidak diizinkan.
    """
    parts = sort_param.split(":")
    field = parts[0]
    direction = parts[1].lower() if len(parts) > 1 else "asc"
    if field not in allowed:
        raise ValueError(f"Field sort '{field}' tidak diizinkan.")
    if direction not in ("asc", "desc"):
        raise ValueError("Arah sort harus 'asc' atau 'desc'.")
    return field, direction
