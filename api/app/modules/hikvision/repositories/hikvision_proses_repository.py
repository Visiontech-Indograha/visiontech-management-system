"""SQL pembentuk absen dari event Hikvision. Tidak commit (batas transaksi di service/CLI)."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from app.core.repository import BaseRepository

# Penanda kolom NOT NULL untuk absen dari mesin (foto perangkat tidak disimpan; bukan kunci berkas).
PENANDA_FOTO = "HIKVISION"

_SQL_INSERT_MASUK = """
WITH t AS (
    SELECT o.office_id, o.latitude, o.longitude, o.clock_in_time, o.clock_out_time,
           COALESCE(mo.latitude, o.latitude) AS mlat, COALESCE(mo.longitude, o.longitude) AS mlng,
           COALESCE(mo.city_boundary_radius_m, o.city_boundary_radius_m) AS city_r,
           COALESCE(mo.in_city_meal_rate, o.in_city_meal_rate) AS in_rate,
           COALESCE(mo.out_city_meal_rate, o.out_city_meal_rate) AS out_rate
    FROM office o
    LEFT JOIN LATERAL (
        SELECT latitude, longitude, city_boundary_radius_m, in_city_meal_rate, out_city_meal_rate
        FROM office WHERE is_main_office = TRUE AND delete_at IS NULL LIMIT 1
    ) mo ON TRUE
    WHERE o.office_id = CAST(:office AS uuid) AND o.delete_at IS NULL
), d AS (
    SELECT t.office_id, t.latitude, t.longitude, t.clock_in_time, t.clock_out_time, t.city_r, t.in_rate,
           t.out_rate, ROUND(6371000 * 2 * ASIN(SQRT(
               POWER(SIN(RADIANS(t.latitude - t.mlat) / 2), 2) +
               COS(RADIANS(t.mlat)) * COS(RADIANS(t.latitude)) *
               POWER(SIN(RADIANS(t.longitude - t.mlng) / 2), 2))))::int AS dist_main
    FROM t
)
INSERT INTO attendance (
    employee_id, attendance_date, target_location_type, office_id, scheduled_in, scheduled_out,
    clock_in_at, in_lat, in_lng, face_match_score, face_photo_path, face_status,
    distance_to_target_m, is_within_attendance_radius, om_approval_status,
    distance_from_main_office_m, city_zone_status, meal_allowance_amount, source, device_event_id
)
SELECT CAST(:emp AS uuid), :tgl, 'OFFICE', d.office_id, d.clock_in_time, d.clock_out_time,
       :at, d.latitude, d.longitude, 0, :foto, 'NOT_CHECKED',
       0, TRUE, 'AUTO_VALID',
       d.dist_main,
       CAST(CASE WHEN d.dist_main <= d.city_r THEN 'DALAM_KOTA' ELSE 'LUAR_KOTA' END AS city_zone_enum),
       CASE WHEN d.dist_main <= d.city_r THEN d.in_rate ELSE d.out_rate END,
       'HIKVISION', CAST(:ev AS uuid)
FROM d
RETURNING attendance_id
"""


class HikvisionProsesRepository(BaseRepository):
    async def lock_employee(self, employee_id: Any) -> None:
        """Kunci yang sama dengan absen aplikasi: tap mesin dan ketukan HP bersamaan diproses berurutan."""
        await self.execute("SELECT pg_advisory_xact_lock(hashtext(:emp))", {"emp": f"attendance:{employee_id}"})

    async def petakan_ulang(self, sertakan_bayangan: bool, devs: list[str] | None = None) -> int:
        """Isi employee_id pada event belum terpetakan bila pemetaannya baru dibuat (event belum diproses)."""
        hasil = await self.fetchall(
            "UPDATE hikvision_event e SET employee_id = m.employee_id "
            "FROM hikvision_employee_map m, hikvision_device d "
            "WHERE e.employee_id IS NULL AND e.diproses_at IS NULL AND d.device_id = e.device_id "
            "AND d.aktif = TRUE AND d.delete_at IS NULL AND (d.mode = 'AKTIF' OR :bay) "
            "AND (CAST(:devs AS uuid[]) IS NULL OR d.device_id = ANY(CAST(:devs AS uuid[]))) "
            "AND m.device_id = e.device_id AND m.employee_no_string = e.employee_no_string "
            "AND m.delete_at IS NULL RETURNING e.event_id",
            {"bay": sertakan_bayangan, "devs": devs},
        )
        return len(hasil)

    async def hitung_tak_terpetakan(self, sertakan_bayangan: bool, devs: list[str] | None = None) -> int:
        return int(
            await self.scalar(
                "SELECT count(*) FROM hikvision_event e JOIN hikvision_device d ON d.device_id = e.device_id "
                "WHERE e.employee_id IS NULL AND e.diproses_at IS NULL AND d.aktif = TRUE AND d.delete_at IS NULL "
                "AND (d.mode = 'AKTIF' OR :bay) "
                "AND (CAST(:devs AS uuid[]) IS NULL OR d.device_id = ANY(CAST(:devs AS uuid[])))",
                {"bay": sertakan_bayangan, "devs": devs},
            )
            or 0
        )

    async def hitung_bayangan_tertunda(self, devs: list[str] | None = None) -> int:
        return int(
            await self.scalar(
                "SELECT count(*) FROM hikvision_event e JOIN hikvision_device d ON d.device_id = e.device_id "
                "WHERE e.diproses_at IS NULL AND d.mode = 'SHADOW' AND d.delete_at IS NULL "
                "AND (CAST(:devs AS uuid[]) IS NULL OR d.device_id = ANY(CAST(:devs AS uuid[])))",
                {"devs": devs},
            )
            or 0
        )

    async def event_tertunda(self, sertakan_bayangan: bool, batas: int, devs: list[str] | None = None) -> Sequence[Any]:
        """Event terpetakan yang belum diproses, urut waktu, dari perangkat aktif (AKTIF, atau juga SHADOW)."""
        return await self.fetchall(
            "SELECT e.event_id, e.event_time, e.employee_id, e.major_event_type, e.minor_event_type, "
            "d.office_id, d.mode "
            "FROM hikvision_event e JOIN hikvision_device d ON d.device_id = e.device_id "
            "JOIN employee emp ON emp.employee_id = e.employee_id AND emp.delete_at IS NULL "
            "WHERE e.diproses_at IS NULL AND e.employee_id IS NOT NULL "
            "AND d.aktif = TRUE AND d.delete_at IS NULL AND (d.mode = 'AKTIF' OR :bay) "
            "AND (CAST(:devs AS uuid[]) IS NULL OR d.device_id = ANY(CAST(:devs AS uuid[]))) "
            "ORDER BY e.event_time, e.event_id LIMIT :n",
            {"bay": sertakan_bayangan, "n": batas, "devs": devs},
        )

    async def absen_hari(self, employee_id: Any, tanggal: date) -> Any:
        """Sesi terbaru karyawan pada tanggal itu (lintas sumber); yang ditolak OM tidak dihitung."""
        return await self.fetchone(
            "SELECT attendance_id, clock_in_at, clock_out_at, om_approval_status, source "
            "FROM attendance WHERE employee_id = CAST(:emp AS uuid) AND attendance_date = :d "
            "AND delete_at IS NULL AND om_approval_status <> 'REJECTED_BY_OM' "
            "ORDER BY clock_in_at DESC LIMIT 1",
            {"emp": str(employee_id), "d": tanggal},
        )

    async def masuk_dari_mesin(
        self, employee_id: Any, office_id: Any, tanggal: date, waktu: datetime, event_id: Any
    ) -> bool:
        row = await self.fetchone(
            _SQL_INSERT_MASUK,
            {"emp": str(employee_id), "office": str(office_id), "tgl": tanggal, "at": waktu,
             "foto": PENANDA_FOTO, "ev": str(event_id)},
        )
        return row is not None

    async def pulang_dari_mesin(self, attendance_id: Any, waktu: datetime, event_id: Any) -> None:
        """Isi/perbarui jam pulang; `source` sesi HP/web tidak diubah."""
        await self.execute(
            "UPDATE attendance SET clock_out_at = :at, device_event_id = CAST(:ev AS uuid), "
            "update_at = NOW() WHERE attendance_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"at": waktu, "ev": str(event_id), "id": str(attendance_id)},
        )

    async def tandai_diproses(self, event_ids: Sequence[Any], kapan: datetime) -> None:
        if not event_ids:
            return
        await self.execute(
            "UPDATE hikvision_event SET diproses_at = :t WHERE event_id = ANY(CAST(:ids AS uuid[]))",
            {"t": kapan, "ids": [str(i) for i in event_ids]},
        )

    async def banding_bayangan(
        self, dari: date, sampai: date, batas: int, major: int, minor: Sequence[int]
    ) -> Sequence[Any]:
        """Pembanding baca-saja: tap pertama/terakhir mesin SHADOW per karyawan-hari vs absen aplikasi."""
        return await self.fetchall(
            "WITH t AS (SELECT e.employee_id, (e.event_time AT TIME ZONE 'Asia/Jakarta')::date AS tgl, "
            "min(e.event_time) AS pertama, max(e.event_time) AS terakhir, count(*) AS jumlah "
            "FROM hikvision_event e JOIN hikvision_device d ON d.device_id = e.device_id "
            "WHERE d.mode = 'SHADOW' AND d.delete_at IS NULL AND e.employee_id IS NOT NULL "
            "AND e.major_event_type = :major AND e.minor_event_type = ANY(:minor) "
            "AND e.event_time >= CAST(:a AS timestamp) AT TIME ZONE 'Asia/Jakarta' "
            "AND e.event_time < (CAST(:b AS timestamp) + interval '1 day') AT TIME ZONE 'Asia/Jakarta' "
            "GROUP BY 1, 2) "
            "SELECT t.employee_id, t.tgl, t.pertama, t.terakhir, t.jumlah, a.clock_in_at, a.clock_out_at, "
            "ROUND(EXTRACT(EPOCH FROM (t.pertama - a.clock_in_at)) / 60)::int AS selisih_masuk_menit, "
            "ROUND(EXTRACT(EPOCH FROM (t.terakhir - a.clock_out_at)) / 60)::int AS selisih_pulang_menit "
            "FROM t LEFT JOIN LATERAL (SELECT clock_in_at, clock_out_at FROM attendance x "
            "WHERE x.employee_id = t.employee_id AND x.attendance_date = t.tgl AND x.delete_at IS NULL "
            "AND x.source IS DISTINCT FROM 'HIKVISION' ORDER BY x.clock_in_at LIMIT 1) a ON TRUE "
            "ORDER BY t.tgl DESC, t.employee_id LIMIT :n",
            {"a": dari, "b": sampai, "n": batas, "major": major, "minor": list(minor)},
        )

    async def banding_perangkat(
        self, device_id: str, dari: date, sampai: date, batas: int, major: int, minor: Sequence[int]
    ) -> tuple[Sequence[Any], Any]:
        """Pembanding baca-saja satu perangkat: baris per karyawan-hari (maks `batas`) + ringkasan jumlah.
        Dua kueri tetap (tidak tumbuh dengan jumlah karyawan)."""
        param = {"d": device_id, "a": dari, "b": sampai, "major": major, "minor": list(minor)}
        rows = await self.fetchall(
            "WITH t AS (SELECT e.employee_id, (e.event_time AT TIME ZONE 'Asia/Jakarta')::date AS tgl, "
            "min(e.event_time) AS pertama, max(e.event_time) AS terakhir, count(*) AS jumlah "
            "FROM hikvision_event e JOIN hikvision_device d ON d.device_id = e.device_id "
            "WHERE d.device_id = CAST(:d AS uuid) AND d.mode = 'SHADOW' AND d.delete_at IS NULL "
            "AND e.employee_id IS NOT NULL AND e.major_event_type = :major AND e.minor_event_type = ANY(:minor) "
            "AND e.event_time >= CAST(:a AS timestamp) AT TIME ZONE 'Asia/Jakarta' "
            "AND e.event_time < (CAST(:b AS timestamp) + interval '1 day') AT TIME ZONE 'Asia/Jakarta' "
            "GROUP BY 1, 2) "
            "SELECT t.employee_id, em.full_name AS employee_name, t.tgl, t.pertama, t.terakhir, t.jumlah, "
            "a.clock_in_at, a.clock_out_at, "
            "ROUND(EXTRACT(EPOCH FROM (t.pertama - a.clock_in_at)) / 60)::int AS selisih_masuk_menit, "
            "ROUND(EXTRACT(EPOCH FROM (t.terakhir - a.clock_out_at)) / 60)::int AS selisih_pulang_menit "
            "FROM t JOIN employee em ON em.employee_id = t.employee_id "
            "LEFT JOIN LATERAL (SELECT clock_in_at, clock_out_at FROM attendance x "
            "WHERE x.employee_id = t.employee_id AND x.attendance_date = t.tgl AND x.delete_at IS NULL "
            "AND x.source IS DISTINCT FROM 'HIKVISION' ORDER BY x.clock_in_at LIMIT 1) a ON TRUE "
            "ORDER BY t.tgl DESC, t.employee_id LIMIT :n",
            {**param, "n": batas},
        )
        ringkas = await self.fetchone(
            "WITH t AS (SELECT e.employee_id, (e.event_time AT TIME ZONE 'Asia/Jakarta')::date AS tgl "
            "FROM hikvision_event e JOIN hikvision_device d ON d.device_id = e.device_id "
            "WHERE d.device_id = CAST(:d AS uuid) AND d.mode = 'SHADOW' AND d.delete_at IS NULL "
            "AND e.employee_id IS NOT NULL AND e.major_event_type = :major AND e.minor_event_type = ANY(:minor) "
            "AND e.event_time >= CAST(:a AS timestamp) AT TIME ZONE 'Asia/Jakarta' "
            "AND e.event_time < (CAST(:b AS timestamp) + interval '1 day') AT TIME ZONE 'Asia/Jakarta' "
            "GROUP BY 1, 2) "
            "SELECT count(*) AS total, count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM attendance x "
            "WHERE x.employee_id = t.employee_id AND x.attendance_date = t.tgl AND x.delete_at IS NULL "
            "AND x.source IS DISTINCT FROM 'HIKVISION')) AS akan_dihasilkan, "
            "(SELECT count(*) FROM hikvision_event e WHERE e.device_id = CAST(:d AS uuid) "
            "AND e.employee_id IS NULL AND e.major_event_type = :major AND e.minor_event_type = ANY(:minor) "
            "AND e.event_time >= CAST(:a AS timestamp) AT TIME ZONE 'Asia/Jakarta' "
            "AND e.event_time < (CAST(:b AS timestamp) + interval '1 day') AT TIME ZONE 'Asia/Jakarta') "
            "AS tak_terpetakan FROM t",
            param,
        )
        return rows, ringkas
