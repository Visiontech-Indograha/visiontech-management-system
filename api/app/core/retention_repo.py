"""app/core/retention_repo.py
SQL job hapus terjadwal. Tanpa commit (transaksi di service). Waktu batas SELALU parameter (`:cutoff`), bukan now()."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.file_cleanup import employee_keys

PERSONAL = "employee_personal_files"
PLACEHOLDER = "dihapus"  # kolom NOT NULL berisi kunci berkas diganti penanda ini


@dataclass(frozen=True)
class ArchiveSpec:
    data_type: str
    table: str
    pk: str
    key_sql: tuple[str, ...] = ()  # SELECT kunci objek milik baris (parameter :id)


SPECS: tuple[ArchiveSpec, ...] = (
    ArchiveSpec("employee_file", "employee_file", "employee_file_id",
                ("SELECT path_file FROM employee_file WHERE employee_file_id = CAST(:id AS uuid)",)),
    ArchiveSpec("vehicle", "vehicle", "vehicle_id", (
        "SELECT photo_path FROM vehicle WHERE vehicle_id = CAST(:id AS uuid)",
        "SELECT path_file FROM vehicle_file WHERE vehicle_id = CAST(:id AS uuid)",
        "SELECT path_file FROM vehicle_inspection WHERE vehicle_id = CAST(:id AS uuid)",
    )),
    ArchiveSpec("tool", "tool", "tool_id",
                ("SELECT photo_path FROM tool WHERE tool_id = CAST(:id AS uuid)",)),
    ArchiveSpec("client", "client", "client_id"),
    ArchiveSpec("company_mess", "company_mess", "mess_id"),
    ArchiveSpec("job_position", "job_position", "position_id"),
    ArchiveSpec("division", "division", "division_id"),
    ArchiveSpec("employee_row", "employee", "employee_id"),
)

# Karyawan keluar > 30 hari yang datanya masih tersisa (idempoten: setelah dianonimkan tidak muncul lagi).
_PERSONAL_PENDING = f"""
e.separated_at IS NOT NULL AND e.separated_at < :cutoff AND (
    e.phone_number IS NOT NULL OR e.face_embedding IS NOT NULL
    OR e.photo_path IS NOT NULL OR e.profile_photo_path IS NOT NULL
    OR EXISTS (SELECT 1 FROM address a WHERE a.employee_id = e.employee_id AND a.address_line <> '-')
    OR EXISTS (SELECT 1 FROM employee_file f WHERE f.employee_id = e.employee_id AND f.path_file <> '{PLACEHOLDER}')
    OR EXISTS (SELECT 1 FROM attendance t WHERE t.employee_id = e.employee_id
               AND (t.face_photo_path <> '{PLACEHOLDER}' OR t.out_of_radius_photo_path IS NOT NULL))
)
"""


async def load_policies(db: AsyncSession) -> dict[str, tuple[int, bool]]:
    rows = (await db.execute(text("SELECT data_type, retention_days, is_active FROM retention_policy"))).all()
    return {r[0]: (int(r[1]), bool(r[2])) for r in rows}


async def count_archive(db: AsyncSession, spec: ArchiveSpec, cutoff: datetime) -> int:
    row = await db.execute(
        text(f"SELECT count(*) FROM {spec.table} WHERE delete_at IS NOT NULL AND delete_at < :cutoff"),
        {"cutoff": cutoff})
    return int(row.scalar_one())


async def next_archive_ids(db: AsyncSession, spec: ArchiveSpec, cutoff: datetime, seen: list[str], n: int) -> list[str]:
    rows = await db.execute(
        text(f"SELECT {spec.pk}::text FROM {spec.table} WHERE delete_at IS NOT NULL AND delete_at < :cutoff "
             f"AND {spec.pk} <> ALL(CAST(:seen AS uuid[])) ORDER BY delete_at LIMIT :n"),
        {"cutoff": cutoff, "seen": seen, "n": n})
    return [r[0] for r in rows.all()]


async def lock_archive_row(db: AsyncSession, spec: ArchiveSpec, cutoff: datetime, row_id: str) -> bool:
    """Kunci baris bila masih arsip & lewat batas (baris yang dipulihkan/dikunci proses lain dilewati)."""
    row = await db.execute(
        text(f"SELECT 1 FROM {spec.table} WHERE {spec.pk} = CAST(:id AS uuid) AND delete_at IS NOT NULL "
             "AND delete_at < :cutoff FOR UPDATE SKIP LOCKED"),
        {"id": row_id, "cutoff": cutoff})
    return row.first() is not None


async def archive_keys(db: AsyncSession, spec: ArchiveSpec, row_id: str) -> list[str]:
    if spec.data_type == "employee_row":
        return await employee_keys(db, row_id)
    keys: list[str] = []
    for sql in spec.key_sql:
        keys.extend(str(r[0]) for r in (await db.execute(text(sql), {"id": row_id})).all() if r[0])
    return list(dict.fromkeys(keys))


async def user_ids_of(db: AsyncSession, employee_id: str) -> list[str]:
    rows = await db.execute(text("SELECT user_id::text FROM users WHERE employee_id = CAST(:id AS uuid)"),
                            {"id": employee_id})
    return [r[0] for r in rows.all()]


async def count_personal(db: AsyncSession, cutoff: datetime) -> int:
    row = await db.execute(text(f"SELECT count(*) FROM employee e WHERE {_PERSONAL_PENDING}"), {"cutoff": cutoff})
    return int(row.scalar_one())


async def next_personal_ids(db: AsyncSession, cutoff: datetime, seen: list[str], n: int) -> list[str]:
    rows = await db.execute(
        text(f"SELECT e.employee_id::text FROM employee e WHERE {_PERSONAL_PENDING} "
             "AND e.employee_id <> ALL(CAST(:seen AS uuid[])) ORDER BY e.separated_at LIMIT :n"),
        {"cutoff": cutoff, "seen": seen, "n": n})
    return [r[0] for r in rows.all()]


async def lock_personal(db: AsyncSession, cutoff: datetime, employee_id: str) -> bool:
    row = await db.execute(
        text(f"SELECT 1 FROM employee e WHERE e.employee_id = CAST(:id AS uuid) AND {_PERSONAL_PENDING} "
             "FOR UPDATE OF e SKIP LOCKED"),
        {"id": employee_id, "cutoff": cutoff})
    return row.first() is not None


async def anonymize_employee(db: AsyncSession, employee_id: str) -> None:
    """Kosongkan data pribadi; baris karyawan & absensi tetap. Kunci berkas sudah diambil pemanggil."""
    p = {"id": employee_id}
    await db.execute(text(
        "UPDATE employee SET photo_path = NULL, profile_photo_path = NULL, face_embedding = NULL, "
        "phone_number = NULL, update_at = now() WHERE employee_id = CAST(:id AS uuid)"), p)
    await db.execute(text(
        "UPDATE address SET address_line = '-', city = '-', postal_code = '-', "
        "delete_at = COALESCE(delete_at, now()), update_at = now() WHERE employee_id = CAST(:id AS uuid)"), p)
    await db.execute(text(
        f"UPDATE employee_file SET path_file = '{PLACEHOLDER}', delete_at = COALESCE(delete_at, now()), "
        "update_at = now() WHERE employee_id = CAST(:id AS uuid)"), p)
    await db.execute(text(
        f"UPDATE attendance SET face_photo_path = '{PLACEHOLDER}', out_of_radius_photo_path = NULL "
        "WHERE employee_id = CAST(:id AS uuid)"), p)
    await db.execute(text(
        f"UPDATE attendance_site_visit SET photo_path = '{PLACEHOLDER}' WHERE attendance_id IN "
        "(SELECT attendance_id FROM attendance WHERE employee_id = CAST(:id AS uuid))"), p)


async def write_audit(db: AsyncSession, action: str, entity_table: str, entity_id: UUID | str,
                      detail: dict[str, Any]) -> None:
    """Audit sistem TANPA nilai sensitif: hanya jenis, id baris, jumlah."""
    await db.execute(
        text("INSERT INTO app_activity_logs (actor_user_id, actor_role, platform, action, entity_table, entity_id, "
             "changed_diff) VALUES (NULL, 'SYSTEM', 'system_cron', :a, :t, CAST(:eid AS uuid), CAST(:d AS jsonb))"),
        {"a": action, "t": entity_table, "eid": str(entity_id), "d": json.dumps(detail)})


async def write_run_log(db: AsyncSession, counts: dict[str, Any], status: str, detail: str | None) -> None:
    await db.execute(
        text("INSERT INTO retention_run_log (mode, counts, status, detail) "
             "VALUES ('terapkan', CAST(:c AS jsonb), :s, :d)"),
        {"c": json.dumps(counts), "s": status, "d": detail})
