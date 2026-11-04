"""
app/shared/idempotency_repository.py

Penyimpanan Idempotency-Key (F-03, tabel `idempotency_keys`). Hanya SQL; kebijakan (kunci, hash,
replay, 409/422) ada di app/api/idempotency.py. Tidak commit: transaksi milik permintaan (get_db).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

_KUNCI = text("SELECT pg_try_advisory_xact_lock(hashtextextended(:kunci, 0))")

_AMBIL = text(
    """
    SELECT request_hash, status, response_body
    FROM idempotency_keys
    WHERE organization_id = CAST(:org AS uuid) AND user_id = CAST(:user AS uuid) AND key = :key
    """
)

_SIMPAN = text(
    """
    INSERT INTO idempotency_keys (organization_id, user_id, key, request_hash, status, response_body)
    VALUES (CAST(:org AS uuid), CAST(:user AS uuid), :key, :hash, :status, CAST(:body AS jsonb))
    ON CONFLICT (organization_id, user_id, key) DO NOTHING
    """
)

_HAPUS_LAMA = text(
    "DELETE FROM idempotency_keys WHERE created_at < now() - make_interval(days => :hari)"
)


@dataclass(frozen=True)
class Respons:
    """Respons yang tersimpan untuk satu kunci: HTTP status dan badan JSON."""

    request_hash: str
    status_code: int
    body: Any


async def kunci_operasi(db: AsyncSession, kunci: str) -> bool:
    """Kunci advisory transaksi (lepas saat commit/rollback). False bila sudah dipegang permintaan lain."""
    hasil: bool = bool((await db.execute(_KUNCI, {"kunci": kunci})).scalar_one())
    return hasil


async def ambil(db: AsyncSession, org: str, user: str, key: str) -> Respons | None:
    baris = (await db.execute(_AMBIL, {"org": org, "user": user, "key": key})).mappings().first()
    if baris is None:
        return None
    badan = baris["response_body"]
    return Respons(
        request_hash=str(baris["request_hash"]),
        status_code=int(baris["status"]),
        body=json.loads(badan) if isinstance(badan, str) else badan,
    )


async def simpan(
    db: AsyncSession, *, org: str, user: str, key: str, request_hash: str, status_code: int, body_json: str
) -> bool:
    """True bila baris tersimpan. False bila baris dengan kunci yang sama sudah ada (seharusnya tidak terjadi
    karena kunci advisory, tetapi dijaga agar tidak menimpa respons lama)."""
    hasil = cast(
        CursorResult[Any],
        await db.execute(
            _SIMPAN,
            {"org": org, "user": user, "key": key, "hash": request_hash, "status": status_code, "body": body_json},
        ),
    )
    return hasil.rowcount == 1


async def hapus_lebih_lama(db: AsyncSession | AsyncConnection, hari: int) -> int:
    """Hapus kunci yang dibuat lebih dari `hari` hari lalu. → jumlah baris yang dihapus."""
    hasil = cast(CursorResult[Any], await db.execute(_HAPUS_LAMA, {"hari": hari}))
    return int(hasil.rowcount)
