"""SQL admin perangkat Hikvision. Tanpa commit. Cakupan kantor lewat `semua` + `offices` (uuid[])."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.core.list_params import MAX_ROWS_UNPAGED
from app.core.repository import BaseRepository, safe_columns

_DEV_COLS = (
    "d.device_id, d.office_id, o.name AS office_name, d.name, d.ip_address, d.http_port, d.serial_no, d.model, "
    "d.mode, d.aktif, d.catatan, d.create_at, d.update_at"
)
_DEV_FROM = "FROM hikvision_device d JOIN office o ON o.office_id = d.office_id"
_SCOPE = "(CAST(:semua AS boolean) OR d.office_id = ANY(CAST(:offices AS uuid[])))"
_MAP_COLS = "m.map_id, m.device_id, m.employee_no_string, m.employee_id, e.employee_no, e.full_name, m.create_at"
_MAP_FROM = "FROM hikvision_employee_map m JOIN employee e ON e.employee_id = m.employee_id"


class HikvisionAdminRepository(BaseRepository):
    async def office(self, office_id: str) -> Any:
        return await self.fetchone(
            "SELECT office_id, name FROM office WHERE office_id = CAST(:o AS uuid) AND delete_at IS NULL",
            {"o": office_id},
        )

    async def devices(self, semua: bool, offices: list[str], office_id: str | None) -> Any:
        return await self.fetchall(
            f"SELECT {_DEV_COLS} {_DEV_FROM} WHERE d.delete_at IS NULL AND {_SCOPE} "
            "AND (CAST(:office AS uuid) IS NULL OR d.office_id = CAST(:office AS uuid)) "
            "ORDER BY o.name, d.name LIMIT :cap",
            {"semua": semua, "offices": offices, "office": office_id, "cap": MAX_ROWS_UNPAGED},
        )

    async def device(self, device_id: str, semua: bool, offices: list[str]) -> Any:
        return await self.fetchone(
            f"SELECT {_DEV_COLS} {_DEV_FROM} WHERE d.device_id = CAST(:d AS uuid) AND d.delete_at IS NULL "
            f"AND {_SCOPE}",
            {"d": device_id, "semua": semua, "offices": offices},
        )

    async def insert_device(self, v: dict[str, Any], token_hash: str, now: datetime) -> str | None:
        """None bila nomor seri sudah dipakai perangkat aktif lain."""
        row = await self.fetchone(
            "INSERT INTO hikvision_device (office_id, name, ip_address, http_port, serial_no, model, token_hash, "
            "aktif, mode, catatan, create_at, update_at) "
            "VALUES (CAST(:office_id AS uuid), :name, :ip_address, :http_port, :serial_no, :model, "
            "CAST(:h AS char(64)), :aktif, :mode, :catatan, :now, :now) "
            "ON CONFLICT (serial_no) WHERE delete_at IS NULL DO NOTHING RETURNING device_id",
            {**v, "h": token_hash, "now": now},
        )
        return None if row is None else str(row.device_id)

    async def update_device(self, device_id: str, changes: dict[str, Any], now: datetime) -> bool:
        """False bila nomor seri bentrok dengan perangkat aktif lain."""
        cols = safe_columns(changes.keys())
        sets = "".join(f"{c} = :{c}, " for c in cols) + "update_at = :now"
        row = await self.fetchone(
            f"UPDATE hikvision_device SET {sets} WHERE device_id = CAST(:d AS uuid) AND delete_at IS NULL "
            "AND NOT EXISTS (SELECT 1 FROM hikvision_device x WHERE x.serial_no = COALESCE(:serial_baru, "
            "hikvision_device.serial_no) AND x.device_id <> hikvision_device.device_id AND x.delete_at IS NULL) "
            "RETURNING device_id",
            {**changes, "serial_baru": changes.get("serial_no"), "d": device_id, "now": now},
        )
        return row is not None

    async def set_token_hash(self, device_id: str, token_hash: str, now: datetime) -> None:
        await self.execute(
            "UPDATE hikvision_device SET token_hash = CAST(:h AS char(64)), update_at = :now "
            "WHERE device_id = CAST(:d AS uuid) AND delete_at IS NULL",
            {"h": token_hash, "now": now, "d": device_id},
        )

    async def soft_delete_device(self, device_id: str, now: datetime) -> None:
        await self.execute(
            "UPDATE hikvision_device SET delete_at = :now, update_at = :now, aktif = FALSE "
            "WHERE device_id = CAST(:d AS uuid) AND delete_at IS NULL",
            {"now": now, "d": device_id},
        )

    # ---- pemetaan ----
    async def maps(self, device_id: str) -> Any:
        return await self.fetchall(
            f"SELECT {_MAP_COLS} {_MAP_FROM} WHERE m.device_id = CAST(:d AS uuid) AND m.delete_at IS NULL "
            "ORDER BY m.employee_no_string LIMIT :cap",
            {"d": device_id, "cap": MAX_ROWS_UNPAGED},
        )

    async def map_by_id(self, device_id: str, map_id: str) -> Any:
        return await self.fetchone(
            f"SELECT {_MAP_COLS} {_MAP_FROM} WHERE m.device_id = CAST(:d AS uuid) "
            "AND m.map_id = CAST(:m AS uuid) AND m.delete_at IS NULL",
            {"d": device_id, "m": map_id},
        )

    async def employee_office(self, employee_id: str) -> Any:
        return await self.fetchone(
            "SELECT employee_id, office_id FROM employee WHERE employee_id = CAST(:e AS uuid) AND delete_at IS NULL",
            {"e": employee_id},
        )

    async def insert_map(self, device_id: str, no: str, employee_id: str) -> str | None:
        row = await self.fetchone(
            "INSERT INTO hikvision_employee_map (device_id, employee_no_string, employee_id) "
            "VALUES (CAST(:d AS uuid), :n, CAST(:e AS uuid)) "
            "ON CONFLICT (device_id, employee_no_string) WHERE delete_at IS NULL DO NOTHING RETURNING map_id",
            {"d": device_id, "n": no, "e": employee_id},
        )
        return None if row is None else str(row.map_id)

    async def update_map(self, device_id: str, map_id: str, employee_id: str) -> bool:
        row = await self.fetchone(
            "UPDATE hikvision_employee_map SET employee_id = CAST(:e AS uuid) "
            "WHERE device_id = CAST(:d AS uuid) AND map_id = CAST(:m AS uuid) AND delete_at IS NULL "
            "RETURNING map_id",
            {"e": employee_id, "d": device_id, "m": map_id},
        )
        return row is not None

    async def delete_map(self, device_id: str, map_id: str, now: datetime) -> bool:
        row = await self.fetchone(
            "UPDATE hikvision_employee_map SET delete_at = :now WHERE device_id = CAST(:d AS uuid) "
            "AND map_id = CAST(:m AS uuid) AND delete_at IS NULL RETURNING map_id",
            {"now": now, "d": device_id, "m": map_id},
        )
        return row is not None

    async def unmapped_numbers(self, device_id: str, sejak: datetime, limit: int) -> Any:
        """Nomor perangkat yang event-nya belum terpetakan (satu kueri, dikelompokkan)."""
        return await self.fetchall(
            "SELECT e.employee_no_string, count(*) AS jumlah FROM hikvision_event e "
            "WHERE e.device_id = CAST(:d AS uuid) AND e.event_time >= :sejak AND e.employee_id IS NULL "
            "AND e.employee_no_string IS NOT NULL AND NOT EXISTS (SELECT 1 FROM hikvision_employee_map m "
            "WHERE m.device_id = e.device_id AND m.employee_no_string = e.employee_no_string "
            "AND m.delete_at IS NULL) "
            "GROUP BY e.employee_no_string ORDER BY count(*) DESC, e.employee_no_string LIMIT :n",
            {"d": device_id, "sejak": sejak, "n": limit},
        )

    async def employees_by_no(self, office_id: str, numbers: list[str]) -> Any:
        return await self.fetchall(
            "SELECT employee_id, employee_no, full_name FROM employee "
            "WHERE employee_no = ANY(:nos) AND office_id = CAST(:o AS uuid) AND delete_at IS NULL",
            {"nos": numbers, "o": office_id},
        )

    async def insert_maps_bulk(self, device_id: str, pairs: list[dict[str, str]]) -> int:
        if not pairs:
            return 0
        rows = await self.fetchall(
            "INSERT INTO hikvision_employee_map (device_id, employee_no_string, employee_id) "
            "SELECT CAST(:d AS uuid), r.no, CAST(r.emp AS uuid) FROM jsonb_to_recordset(CAST(:rows AS jsonb)) "
            "AS r(no text, emp text) "
            "ON CONFLICT (device_id, employee_no_string) WHERE delete_at IS NULL DO NOTHING RETURNING map_id",
            {"d": device_id, "rows": json.dumps(pairs)},
        )
        return len(rows)

    async def apply_maps_to_events(self, device_id: str, batch: int) -> int:
        """Isi `employee_id` event yang masih NULL dari pemetaan aktif, satu kelompok (maks `batch`) per panggilan."""
        rows = await self.fetchall(
            "WITH t AS (SELECT e.event_id, m.employee_id FROM hikvision_event e "
            "JOIN hikvision_employee_map m ON m.device_id = e.device_id "
            "AND m.employee_no_string = e.employee_no_string AND m.delete_at IS NULL "
            "WHERE e.device_id = CAST(:d AS uuid) AND e.employee_id IS NULL "
            "ORDER BY e.event_time DESC LIMIT :n FOR UPDATE OF e SKIP LOCKED) "
            "UPDATE hikvision_event ev SET employee_id = t.employee_id FROM t "
            "WHERE ev.event_id = t.event_id RETURNING ev.event_id",
            {"d": device_id, "n": batch},
        )
        return len(rows)

    # ---- status ----
    async def event_counts(self, device_id: str, t24: datetime, t7: datetime) -> Any:
        return await self.fetchone(
            "SELECT count(*) FILTER (WHERE event_time >= :t24) AS c24, count(*) AS c7, "
            "count(*) FILTER (WHERE employee_id IS NULL) AS belum FROM hikvision_event "
            "WHERE device_id = CAST(:d AS uuid) AND event_time >= :t7",
            {"d": device_id, "t24": t24, "t7": t7},
        )

    async def last_received(self, device_id: str) -> Any:
        return await self.scalar(
            "SELECT received_at FROM hikvision_event WHERE device_id = CAST(:d AS uuid) "
            "ORDER BY event_time DESC LIMIT 1",
            {"d": device_id},
        )

    async def duplicate_groups(self, device_id: str, t7: datetime) -> int:
        return int(
            await self.scalar(
                "SELECT count(*) FROM (SELECT 1 FROM hikvision_event WHERE device_id = CAST(:d AS uuid) "
                "AND event_time >= :t7 AND employee_no_string IS NOT NULL "
                "GROUP BY employee_no_string, event_time, major_event_type, minor_event_type "
                "HAVING count(*) > 1) x",
                {"d": device_id, "t7": t7},
            )
            or 0
        )
