"""
app/crud/crud_audit.py
Riwayat kejadian audit organisasi (VIEW_AUDIT). Disaring `organization_id` secara eksplisit — tidak hanya
mengandalkan RLS (T-12).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase

_FILTER = """
    WHERE organization_id = CAST(:org AS uuid)
      AND (CAST(:entity_type AS text) IS NULL OR entity_type = CAST(:entity_type AS text))
"""


class CRUDAudit(CRUDBase):
    """Kueri baca `vms.audit_event` (aplikasi tidak pernah menyunting audit)."""

    async def count(self, org_id: UUID | str, entity_type: str | None) -> int:
        """Jumlah kejadian audit organisasi, opsional per jenis entitas."""
        row = await self.fetchone(f"SELECT COUNT(*) AS n FROM vms.audit_event {_FILTER}",
                                  {"org": org_id, "entity_type": entity_type})
        return int(row.n) if row else 0

    async def list_page(self, org_id: UUID | str, entity_type: str | None, limit: int, offset: int) -> list[Any]:
        """Satu halaman kejadian audit, terbaru lebih dulu."""
        return list(await self.fetchall(f"""
            SELECT id, occurred_at, actor_label, action, entity_type, entity_id, detail, changes
              FROM vms.audit_event {_FILTER}
             ORDER BY occurred_at DESC
             LIMIT :limit OFFSET :offset
        """, {"org": org_id, "entity_type": entity_type, "limit": limit, "offset": offset}))
