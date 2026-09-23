"""
Konteks permintaan untuk RLS dan audit di basis data (`app.user_id`, `app.organization_id`,
`app.actor_label` — dibaca `current_user_id()`, `current_org_id()`, `tg_audit_row()`).

`set_config(..., true)` = SET LOCAL: berlaku sampai transaksi selesai, jadi tidak bocor ke
permintaan lain yang memakai koneksi yang sama (R-08). Satu `SELECT` dengan parameter bind —
`SET LOCAL x = $1` tidak bisa dipakai karena SET tidak menerima parameter, dan asyncpg menolak
beberapa perintah dalam satu prepared statement.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

_SET_CONTEXT = text(
    """
    SELECT set_config('app.user_id', :user_id, true),
           set_config('app.organization_id', :organization_id, true),
           set_config('app.actor_label', :actor_label, true)
    """
)


async def set_request_context(
    db: AsyncSession | AsyncConnection,
    *,
    user_id: str,
    organization_id: str,
    actor_label: str,
) -> None:
    await db.execute(
        _SET_CONTEXT,
        {"user_id": user_id, "organization_id": organization_id, "actor_label": actor_label},
    )
