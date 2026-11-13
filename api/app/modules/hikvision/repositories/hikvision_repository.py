"""SQL perangkat dan event Hikvision. Tidak commit (transaksi di service/get_db atau CLI)."""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from app.core.repository import BaseRepository


class HikvisionRepository(BaseRepository):
    async def device_by_token_hash(self, token_hash: str) -> Any:
        """Perangkat aktif menurut hash token (indeks unik uq_hikvision_device_token_hash)."""
        return await self.fetchone(
            "SELECT device_id, serial_no, ip_address, mode, token_hash FROM hikvision_device "
            "WHERE token_hash = CAST(:h AS char(64)) AND aktif = TRUE AND delete_at IS NULL",
            {"h": token_hash},
        )

    async def device_by_serial(self, serial: str) -> Any:
        return await self.fetchone(
            "SELECT device_id, serial_no, ip_address, http_port, mode FROM hikvision_device "
            "WHERE serial_no = :s AND delete_at IS NULL",
            {"s": serial},
        )

    async def latest_pull_time(self, device_id: Any, mulai: Any, akhir: Any) -> Any:
        return await self.scalar(
            "SELECT max(event_time) FROM hikvision_event "
            "WHERE device_id = :d AND sumber = 'PULL' AND event_time >= :a AND event_time <= :b",
            {"d": device_id, "a": mulai, "b": akhir},
        )

    async def insert_events(self, device_id: Any, sumber: str, rows: Sequence[dict[str, Any]]) -> int:
        """Sisipkan satu kelompok event sekaligus (satu pernyataan). Duplikat (kunci unik) dilewati.
        `employee_id` diisi dari hikvision_employee_map bila ada (kosong = NULL). Mengembalikan jumlah baris baru."""
        if not rows:
            return 0
        hasil = await self.fetchall(
            "INSERT INTO hikvision_event (device_id, serial_no_event, event_key, major_event_type, "
            "minor_event_type, event_time, employee_no_string, card_no, verify_mode, payload, sumber, employee_id) "
            "SELECT CAST(:d AS uuid), r.serial_no_event, CAST(r.event_key AS char(64)), r.major, r.minor, "
            "r.event_time, r.employee_no_string, r.card_no, r.verify_mode, r.payload, :sumber, m.employee_id "
            "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(serial_no_event int, event_key text, major int, "
            "minor int, event_time timestamptz, employee_no_string text, card_no text, verify_mode text, "
            "payload jsonb) "
            "LEFT JOIN hikvision_employee_map m ON m.device_id = CAST(:d AS uuid) "
            "AND m.employee_no_string = r.employee_no_string AND m.delete_at IS NULL "
            "ON CONFLICT DO NOTHING RETURNING event_id",
            {"d": str(device_id), "sumber": sumber, "rows": json.dumps(list(rows))},
        )
        return len(hasil)
