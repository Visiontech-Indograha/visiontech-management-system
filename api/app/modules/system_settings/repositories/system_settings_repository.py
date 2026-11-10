"""SQL tabel system_setting. Tidak commit."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.core.repository import BaseRepository


class SystemSettingsRepository(BaseRepository):
    async def rows(self) -> dict[str, tuple[Any, datetime]]:
        found = await self.fetchall("SELECT key, value, update_at FROM system_setting")
        return {r.key: (r.value, r.update_at) for r in found}

    async def lock_rows(self, keys: list[str]) -> dict[str, Any]:
        """Kunci baris yang ada (urut kunci, tanpa deadlock) lalu kembalikan nilai sebelumnya."""
        found = await self.fetchall(
            "SELECT key, value FROM system_setting WHERE key = ANY(:keys) ORDER BY key FOR UPDATE", {"keys": keys}
        )
        return {r.key: r.value for r in found}

    async def upsert(self, key: str, value: bool, user_id: str) -> None:
        await self.execute(
            "INSERT INTO system_setting (key, value, updated_by) VALUES (:k, CAST(:v AS jsonb), CAST(:u AS uuid)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_by = EXCLUDED.updated_by, "
            "update_at = now()",
            {"k": key, "v": json.dumps(value), "u": user_id},
        )
