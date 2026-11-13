"""Penjadwal pengingat dokumen (STNK/KIR/pajak/asuransi kendaraan dan SIM karyawan).

Tahap dihitung dari sisa hari ke tanggal jatuh tempo: T30, T21, T14 (tepat pada harinya), lalu DAILY setiap hari
dari H-`harian_mulai_hari` sampai H0 dan setelah lewat tempo (maksimal `LEWAT_MAKS_HARI`). Idempoten lewat tabel
`document_reminder`: baris diklaim dulu (ON CONFLICT DO NOTHING), notifikasi hanya dikirim bila klaim berhasil,
semuanya satu transaksi, sehingga dijalankan ulang pada hari yang sama tidak mengirim ganda. Dokumen yang sudah
diganti (`replaced`) atau tidak aktif tidak pernah dipilih. Kueri konstan terhadap jumlah dokumen (tanpa N+1).
Jam disuntikkan lewat parameter `today` (default `jakarta_now`)."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import jakarta_now
from app.modules.notifications.services.notification_service import NotificationService

LEWAT_MAKS_HARI = 30
_TAHAP_AMBANG = {30: "T30", 21: "T21", 14: "T14"}
KIND = "DOC_EXPIRY"


def hitung_tahap(days_left: int, ambang: Iterable[int], harian_mulai: int) -> str | None:
    """Tahap pengingat untuk sisa hari tertentu, atau None bila hari ini bukan hari pengingat."""
    if days_left <= harian_mulai:
        return "DAILY" if days_left >= -LEWAT_MAKS_HARI else None
    if days_left in set(ambang):
        return _TAHAP_AMBANG.get(days_left)
    return None


@dataclass
class Ringkasan:
    kandidat: int = 0
    dikirim: int = 0
    dilewati_sudah_terkirim: int = 0
    tanpa_penerima: int = 0
    notifikasi: int = 0
    per_tahap: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "per_tahap": dict(self.per_tahap)}


_DOCS_SQL = """
    SELECT 'VEHICLE_DOCUMENT' AS kind, vd.vehicle_document_id AS doc_id, vd.office_id, vd.vehicle_id,
           CAST(NULL AS uuid) AS employee_id, dt.nama || ' ' || v.number_plate AS label, vd.expired_on AS due,
           dt.ambang_hari, dt.harian_mulai_hari
    FROM vehicle_document vd
    JOIN document_type dt ON dt.code = vd.doc_type_code AND dt.aktif
    JOIN vehicle v ON v.vehicle_id = vd.vehicle_id AND v.delete_at IS NULL
    WHERE vd.status = 'active' AND vd.delete_at IS NULL
      AND (CAST(:office AS uuid) IS NULL OR vd.office_id = CAST(:office AS uuid))
      AND vd.expired_on BETWEEN CAST(:today AS date) - CAST(:lewat AS int) AND CAST(:today AS date) + 60
    UNION ALL
    SELECT 'EMPLOYEE_FILE', ef.employee_file_id, e.office_id, CAST(NULL AS uuid), ef.employee_id,
           dt.nama || ' ' || e.full_name, CAST(ef.expired_at AT TIME ZONE 'Asia/Jakarta' AS date),
           dt.ambang_hari, dt.harian_mulai_hari
    FROM employee_file ef
    JOIN employee e ON e.employee_id = ef.employee_id AND e.delete_at IS NULL
    JOIN document_type dt ON dt.code = 'SIM' AND dt.aktif
    WHERE ef.type IN ('SIM_A', 'SIM_B') AND ef.status = 'active' AND ef.delete_at IS NULL
      AND ef.expired_at IS NOT NULL AND (CAST(:office AS uuid) IS NULL OR e.office_id = CAST(:office AS uuid))
      AND CAST(ef.expired_at AT TIME ZONE 'Asia/Jakarta' AS date)
          BETWEEN CAST(:today AS date) - CAST(:lewat AS int) AND CAST(:today AS date) + 60
"""


async def _hse_om_by_office(db: AsyncSession, offices: list[str]) -> dict[str, list[str]]:
    """HSE dan OM aktif per kantor: peran utama di kantor itu atau penugasan peran ganda aktif di kantor itu."""
    from sqlalchemy import text
    rows = (await db.execute(text(
        "SELECT CAST(o.office_id AS text) AS office, CAST(u.user_id AS text) AS uid "
        "FROM office o JOIN employee e ON e.office_id = o.office_id AND e.delete_at IS NULL "
        "JOIN users u ON u.employee_id = e.employee_id AND u.is_active AND u.delete_at IS NULL "
        "WHERE o.office_id = ANY(CAST(:o AS uuid[])) AND CAST(u.system_role AS text) IN ('HSE', 'OPERATIONAL_MANAGER') "
        "UNION "
        "SELECT CAST(a.office_id AS text), CAST(u.user_id AS text) FROM user_role_assignment a "
        "JOIN users u ON u.user_id = a.user_id AND u.is_active AND u.delete_at IS NULL "
        "WHERE a.office_id = ANY(CAST(:o AS uuid[])) AND a.delete_at IS NULL "
        "AND CAST(a.role AS text) IN ('HSE', 'OPERATIONAL_MANAGER')"
    ), {"o": offices})).all()
    out: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        out[r.office].append(r.uid)
    return out


async def _drivers_by_vehicle(db: AsyncSession, vehicles: list[str], today: date) -> dict[str, list[str]]:
    from sqlalchemy import text
    rows = (await db.execute(text(
        "SELECT CAST(d.vehicle_id AS text) AS vid, CAST(u.user_id AS text) AS uid FROM vehicle_driver d "
        "JOIN users u ON u.employee_id = d.employee_id AND u.is_active AND u.delete_at IS NULL "
        "WHERE d.vehicle_id = ANY(CAST(:v AS uuid[])) AND d.delete_at IS NULL "
        "AND d.mulai_on <= CAST(:t AS date) AND (d.selesai_on IS NULL OR d.selesai_on >= CAST(:t AS date))"
    ), {"v": vehicles, "t": today})).all()
    out: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        out[r.vid].append(r.uid)
    return out


async def _users_of_employees(db: AsyncSession, employees: list[str]) -> dict[str, str]:
    from sqlalchemy import text
    rows = (await db.execute(text(
        "SELECT CAST(employee_id AS text) AS eid, CAST(user_id AS text) AS uid FROM users "
        "WHERE employee_id = ANY(CAST(:e AS uuid[])) AND is_active AND delete_at IS NULL"
    ), {"e": employees})).all()
    return {r.eid: r.uid for r in rows}


def _kalimat(label: str, days_left: int) -> tuple[str, str]:
    if days_left > 0:
        return f"{label} jatuh tempo {days_left} hari lagi", "Segera urus perpanjangannya."
    if days_left == 0:
        return f"{label} jatuh tempo hari ini", "Segera urus perpanjangannya."
    return f"{label} sudah lewat jatuh tempo {-days_left} hari", "Dokumen ini sudah tidak berlaku. Segera perpanjang."


async def jalankan(
    db: AsyncSession, *, today: date | None = None, dry_run: bool = False, office_id: str | None = None,
) -> Ringkasan:
    """Hitung dan kirim pengingat. Pemanggil yang commit (CLI: satu transaksi). `dry_run` tidak menulis apa pun.
    `office_id` membatasi pada satu kantor (None = semua)."""
    from sqlalchemy import text
    hari = today or jakarta_now().date()
    ring = Ringkasan()
    docs = (await db.execute(text(_DOCS_SQL), {"today": hari, "lewat": LEWAT_MAKS_HARI, "office": office_id})).all()
    due: list[tuple[Any, str, int]] = []
    for d in docs:
        left = (d.due - hari).days
        tahap = hitung_tahap(left, d.ambang_hari or [], d.harian_mulai_hari)
        if tahap:
            due.append((d, tahap, left))
    ring.kandidat = len(due)
    if not due:
        return ring

    staff = await _hse_om_by_office(db, sorted({str(d.office_id) for d, _, _ in due}))
    vehicles = sorted({str(d.vehicle_id) for d, _, _ in due if d.vehicle_id})
    drivers = await _drivers_by_vehicle(db, vehicles, hari) if vehicles else {}
    emp_ids = sorted({str(d.employee_id) for d, _, _ in due if d.employee_id})
    owners = await _users_of_employees(db, emp_ids) if emp_ids else {}
    notifier = NotificationService(db)

    for d, tahap, left in due:
        penerima = set(staff.get(str(d.office_id), []))
        if d.vehicle_id:
            penerima |= set(drivers.get(str(d.vehicle_id), []))
        if d.employee_id and str(d.employee_id) in owners:
            penerima.add(owners[str(d.employee_id)])
        if not penerima:
            ring.tanpa_penerima += 1
            continue
        if dry_run:
            ring.dikirim += 1
            ring.notifikasi += len(penerima)
            ring.per_tahap[tahap] += 1
            continue
        klaim = await db.execute(text(
            "INSERT INTO document_reminder (office_id, doc_kind, doc_id, due_date, stage, send_date, "
            "jumlah_penerima) VALUES (:o, :k, :d, :due, :s, :t, :n) ON CONFLICT DO NOTHING RETURNING reminder_id"
        ), {"o": d.office_id, "k": d.kind, "d": d.doc_id, "due": d.due, "s": tahap, "t": hari, "n": len(penerima)})
        if klaim.first() is None:
            ring.dilewati_sudah_terkirim += 1
            continue
        judul, isi = _kalimat(d.label, left)
        await notifier.notify_users(sorted(penerima), KIND, judul, isi, target="document_expiry")
        ring.dikirim += 1
        ring.notifikasi += len(penerima)
        ring.per_tahap[tahap] += 1
    return ring
