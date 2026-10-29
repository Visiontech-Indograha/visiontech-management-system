"""
app/crud/crud_audit.py
Riwayat kejadian audit terpartisi bulanan (public.app_activity_logs)
dan registry backup (public.system_backup_registry).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository, escape_like

_JOINS = """
    LEFT JOIN public.users u ON u.user_id = a.actor_user_id
    LEFT JOIN public.employee e ON e.employee_id = u.employee_id
"""
# Cari `q` = awalan aksi / tabel / nama pelaku (indeks-friendly); rentang tanggal memangkas partisi bulanan.
_FILTER = """
    WHERE (CAST(:entity_type AS text) IS NULL OR a.entity_table = CAST(:entity_type AS text))
      AND (CAST(:q AS text) IS NULL OR a.action ILIKE CAST(:q AS text) OR a.entity_table ILIKE CAST(:q AS text)
           OR e.full_name ILIKE CAST(:q AS text))
      AND (CAST(:date_from AS date) IS NULL OR a.created_at >= CAST(:date_from AS date))
      AND (CAST(:date_to AS date) IS NULL OR a.created_at < CAST(:date_to AS date) + 1)
"""


def _params(entity_type: str | None, q: str | None, date_from: Any, date_to: Any) -> dict[str, Any]:
    return {
        "entity_type": entity_type,
        "q": f"{escape_like(q)}%" if q else None,
        "date_from": date_from,
        "date_to": date_to,
    }


class AuditRepository(BaseRepository):
    """Repositori jejak audit aktivitas pengguna (tabel app_activity_logs)."""
    """Kueri baca `public.app_activity_logs` dan `public.system_backup_registry`."""

    async def count(
        self,
        org_id: UUID | str,
        entity_type: str | None,
        q: str | None = None,
        date_from: Any = None,
        date_to: Any = None,
    ) -> int:
        """Jumlah kejadian audit aktivitas, opsional per jenis entitas, kata kunci, dan rentang tanggal."""
        row = await self.fetchone(
            f"SELECT COUNT(*) AS n FROM public.app_activity_logs a {_JOINS} {_FILTER}",
            _params(entity_type, q, date_from, date_to),
        )
        return int(row.n) if row else 0

    async def list_page(
        self,
        org_id: UUID | str,
        entity_type: str | None,
        limit: int,
        offset: int,
        q: str | None = None,
        date_from: Any = None,
        date_to: Any = None,
    ) -> list[Any]:
        """Satu halaman kejadian audit dari tabel terpartisi bulanan, terbaru lebih dulu."""
        return list(
            await self.fetchall(
                f"""
            SELECT
                a.log_id AS id,
                a.created_at AS occurred_at,
                COALESCE(e.full_name || ' (' || a.actor_role || ')', a.actor_role) AS actor_label,
                a.action,
                a.entity_table AS entity_type,
                a.entity_id,
                'Platform: ' || a.platform || ', IP: ' || COALESCE(host(a.ip_address), '-')
                    || ', GPS: ' || COALESCE(a.gps_location, '-') AS detail,
                a.changed_diff AS changes
            FROM public.app_activity_logs a
            {_JOINS}
            {_FILTER}
            ORDER BY a.created_at DESC
            LIMIT :limit OFFSET :offset
        """,
                {**_params(entity_type, q, date_from, date_to), "limit": limit, "offset": offset},
            )
        )

    async def list_backups(self) -> list[Any]:
        """Daftar arsip backup sistem dari system_backup_registry."""
        return list(
            await self.fetchall(
                """
            SELECT
                b.backup_id AS id,
                b.backup_cycle,
                b.period_start,
                b.period_end,
                b.file_path_url,
                b.compressed_size_mb,
                b.sha256_checksum,
                b.status,
                b.created_at
            FROM public.system_backup_registry b
            ORDER BY b.created_at DESC
        """,
                {},
            )
        )


# Alias backward compatibility
CRUDAudit = AuditRepository
