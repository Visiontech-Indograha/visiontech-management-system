"""
Catatan audit perubahan data master (buat/ubah/hapus) di app_activity_logs.

Hanya bidang dalam daftar putih `fields` yang dicatat nilai lamanya/barunya. Bidang di `masked` (alamat,
nomor telepon, dan sejenisnya) hanya dicatat NAMANYA bila berubah, tanpa nilai. Bidang lain tidak masuk audit.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.hard_delete import write_delete_audit
from app.core.security import CurrentUser


def _get(src: Any, key: str) -> Any:
    if src is None:
        return None
    if isinstance(src, Mapping):
        return src.get(key)
    return getattr(src, key, None)


def _plain(value: Any) -> Any:
    """Nilai -> tipe JSON (tanggal/UUID/Decimal/enum jadi teks)."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    inner = getattr(value, "value", None)
    if isinstance(inner, str | int):
        return inner
    return str(value)


def build_changes(
    before: Any,
    after: Any,
    fields: Iterable[str],
    masked: Iterable[str] = (),
) -> dict[str, Any]:
    """Ringkasan beda: {"changes": {f: {"old","new"}}, "masked_changed": [f]}; kosong bila tidak ada beda.

    `before` None = pembuatan (hanya nilai baru); `after` None = penghapusan (hanya nilai lama).
    """
    both = before is not None and after is not None
    changes: dict[str, dict[str, Any]] = {}
    for f in fields:
        old, new = _plain(_get(before, f)), _plain(_get(after, f))
        if both and old == new:
            continue
        entry: dict[str, Any] = {}
        if before is not None:
            entry["old"] = old
        if after is not None:
            entry["new"] = new
        changes[f] = entry
    masked_changed = [f for f in masked if not both or _plain(_get(before, f)) != _plain(_get(after, f))]
    out: dict[str, Any] = {}
    if changes:
        out["changes"] = changes
    if masked_changed:
        out["masked_changed"] = masked_changed
    return out


async def record_audit(
    db: AsyncSession,
    actor: CurrentUser,
    *,
    action: str,
    entity_type: str,
    entity_id: UUID | str,
    before: Any = None,
    after: Any = None,
    fields: Iterable[str] = (),
    masked: Iterable[str] = (),
    extra: dict[str, Any] | None = None,
    skip_if_empty: bool = False,
) -> None:
    """Tulis satu catatan audit; `skip_if_empty` melewatkan ubah-tanpa-beda."""
    detail = build_changes(before, after, fields, masked)
    if skip_if_empty and not detail:
        return
    await write_delete_audit(
        db,
        actor_user_id=actor.user_id,
        actor_role=actor.role,
        actor_email=actor.email,
        entity_type=entity_type,
        entity_id=UUID(str(entity_id)),
        action=action,
        detail={**(extra or {}), **detail},
    )
