"""
app/crud/crud_member_report.py
Laporan harian berjenjang (alur SK v2 PR2, flowchart SK2-E): laporan anggota untuk ketua, dan data dokumen
laporan harian/mingguan yang sudah disetujui PM.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDMemberReport(CRUDBase):
    """
    Kelas operasi CRUD untuk menangani Laporan Harian Anggota (berjenjang).
    Mengelola draf dan pengiriman laporan harian dari anggota ke ketua proyek (PM),
    beserta dokumen-dokumen yang dilampirkan.
    """

    async def employee_of(self, user_id: UUID | str) -> str | None:
        """
        Mendapatkan ID karyawan berdasarkan ID pengguna (user).

        Args:
            user_id (UUID | str): ID pengguna.

        Returns:
            str | None: ID karyawan dalam bentuk string, atau None.
        """
        # Mengambil ID karyawan dari app_user
        value = await self.scalar("SELECT CAST(employee_id AS text) FROM vms.app_user WHERE id = :uid", {"uid": user_id})
        return str(value) if value else None

    async def list_for_day(self, day_id: UUID | str) -> list[Any]:
        """
        Mengambil semua laporan harian dari anggota-anggota pada hari kerja (SK) tertentu,
        baik yang sudah dikirim maupun yang masih berupa draf (untuk dilihat oleh Ketua/PM).

        Args:
            day_id (UUID | str): ID hari kerja (work_plan_day).

        Returns:
            list[Any]: Daftar laporan beserta detail karyawan dan lampiran berkas.
        """
        # Melakukan JOIN dengan tabel employee untuk mendapatkan nama dan jabatan anggota
        # Menggunakan subquery (ARRAY) untuk mengumpulkan file_id bukti dari tabel member_report_evidence
        return list(await self.fetchall(
            """
            SELECT r.id, CAST(r.employee_id AS text) AS employee_id, e.full_name, e.position, r.status, r.body,
                   r.obstacle, r.sent_at,
                   COALESCE(ARRAY(SELECT CAST(ev.file_id AS text) FROM vms.member_report_evidence ev
                                  WHERE ev.member_report_id = r.id ORDER BY ev.file_id), '{}') AS evidence_file_ids,
                   COALESCE((SELECT jsonb_agg(jsonb_build_object('file_id', ev.file_id, 'slot_label', ev.slot_label,
                                                                 'source', ev.source) ORDER BY ev.file_id)
                             FROM vms.member_report_evidence ev WHERE ev.member_report_id = r.id),
                            '[]'::jsonb) AS evidence
            FROM vms.member_daily_report r JOIN vms.employee e ON e.id = r.employee_id
            WHERE r.work_plan_day_id = :day
            ORDER BY r.sent_at NULLS LAST, e.full_name
            """,
            {"day": day_id},
        ))

    async def mine(self, day_id: UUID | str, employee_id: str) -> Any:
        """
        Mengambil satu laporan harian milik karyawan spesifik pada hari tertentu.

        Args:
            day_id (UUID | str): ID hari kerja.
            employee_id (str): ID karyawan (anggota).

        Returns:
            Any: Data laporan anggota beserta lampiran buktinya, atau None jika belum ada.
        """
        # Mengambil data laporan khusus untuk karyawan tertentu (WHERE employee_id = :emp)
        return await self.fetchone(
            """
            SELECT r.id, CAST(r.employee_id AS text) AS employee_id, e.full_name, e.position, r.status, r.body,
                   r.obstacle, r.sent_at,
                   COALESCE(ARRAY(SELECT CAST(ev.file_id AS text) FROM vms.member_report_evidence ev
                                  WHERE ev.member_report_id = r.id ORDER BY ev.file_id), '{}') AS evidence_file_ids,
                   COALESCE((SELECT jsonb_agg(jsonb_build_object('file_id', ev.file_id, 'slot_label', ev.slot_label,
                                                                 'source', ev.source) ORDER BY ev.file_id)
                             FROM vms.member_report_evidence ev WHERE ev.member_report_id = r.id),
                            '[]'::jsonb) AS evidence
            FROM vms.member_daily_report r JOIN vms.employee e ON e.id = r.employee_id
            WHERE r.work_plan_day_id = :day AND r.employee_id = CAST(:emp AS uuid)
            """,
            {"day": day_id, "emp": employee_id},
        )

    async def save(self, day_id: UUID | str, employee_id: str, body: str, obstacle: str) -> Any:
        """
        Menyimpan draf laporan harian anggota (insert atau update).
        Hanya bisa mengupdate jika laporan masih berstatus 'DRAFT'. Jika sudah dikirim ('SENT'),
        data tidak akan berubah.

        Args:
            day_id (UUID | str): ID hari kerja.
            employee_id (str): ID karyawan.
            body (str): Isi laporan.
            obstacle (str): Kendala yang dilaporkan.

        Returns:
            Any: ID laporan (Row) yang berhasil disimpan/diubah, atau None.
        """
        # Melakukan UPSERT (INSERT ... ON CONFLICT DO UPDATE) untuk data laporan
        # Pembaruan hanya terjadi (WHERE ... status = 'DRAFT') untuk mencegah perubahan setelah dikirim
        return await self.fetchone(
            """
            INSERT INTO vms.member_daily_report (work_plan_day_id, employee_id, body, obstacle)
            VALUES (:day, CAST(:emp AS uuid), :body, :obstacle)
            ON CONFLICT (work_plan_day_id, employee_id) DO UPDATE
               SET body = EXCLUDED.body, obstacle = EXCLUDED.obstacle, updated_at = now()
             WHERE vms.member_daily_report.status = 'DRAFT'
            RETURNING id
            """,
            {"day": day_id, "emp": employee_id, "body": body, "obstacle": obstacle},
        )

    async def replace_evidence(self, report_id: UUID | str, items: list[tuple[str, str | None, str]]) -> None:
        """
        Mengganti seluruh lampiran bukti laporan anggota dengan daftar ID file yang baru.

        Args:
            report_id (UUID | str): ID laporan.
            file_ids (Iterable[UUID]): Daftar ID file lampiran baru.
        """
        # Berkas yang sudah punya label/sumber dan kembali tanpa metadata mempertahankan metadata lamanya.
        old = {str(r.file_id): (r.slot_label, r.source) for r in await self.fetchall(
            "SELECT file_id, slot_label, source FROM vms.member_report_evidence WHERE member_report_id = :rid",
            {"rid": report_id})}
        items = [(f, old[f][0], old[f][1]) if (s is None and src == "CAMERA" and f in old) else (f, s, src)
                 for f, s, src in items]
        # Menghapus relasi lampiran bukti (evidence) lama untuk laporan ini
        await self.execute("DELETE FROM vms.member_report_evidence WHERE member_report_id = :rid", {"rid": report_id})
        if items:
            # Menyisipkan (bulk insert) berkas bukti beserta slot template dan sumbernya (unnest paralel)
            await self.execute(
                """
                INSERT INTO vms.member_report_evidence (member_report_id, file_id, slot_label, source)
                SELECT :rid, CAST(f AS uuid), NULLIF(s, ''), src
                FROM unnest(CAST(:fids AS text[]), CAST(:slots AS text[]), CAST(:srcs AS text[])) AS t(f, s, src)
                """,
                {"rid": report_id, "fids": [i[0] for i in items], "slots": [i[1] or "" for i in items],
                 "srcs": [i[2] for i in items]},
            )

    async def send(self, day_id: UUID | str, employee_id: str) -> Any:
        """
        Mengirim laporan anggota (mengubah status dari DRAFT menjadi SENT).
        Hanya berlaku jika isi laporan (body) memiliki panjang minimal 10 karakter.

        Args:
            day_id (UUID | str): ID hari kerja.
            employee_id (str): ID karyawan pembuat laporan.

        Returns:
            Any: ID laporan yang berhasil dikirim, atau None jika gagal/tidak memenuhi syarat.
        """
        # Memperbarui status laporan dan mencatat waktu pengiriman, jika statusnya masih DRAFT dan
        # panjang teks body valid (>= 10)
        return await self.fetchone(
            """
            UPDATE vms.member_daily_report SET status = 'SENT', sent_at = now(), updated_at = now()
             WHERE work_plan_day_id = :day AND employee_id = CAST(:emp AS uuid) AND status = 'DRAFT'
               AND length(btrim(body)) >= 10
            RETURNING id
            """,
            {"day": day_id, "emp": employee_id},
        )

    async def day_info(self, day_id: UUID | str) -> Any:
        """
        Mendapatkan informasi dasar dari hari kerja (SK), seperti tanggal, judul, dan ID rencana (plan).

        Args:
            day_id (UUID | str): ID hari kerja.

        Returns:
            Any: Informasi hari kerja.
        """
        # Mengambil atribut dasar hari kerja
        return await self.fetchone(
            "SELECT d.work_date, d.title, CAST(d.work_plan_id AS text) AS plan_id FROM vms.work_plan_day d WHERE d.id = :day",
            {"day": day_id})

    # ── Dokumen laporan (A4) ──────────────────────────────────────────────────────────────────
    async def plan_header(self, plan_id: UUID | str) -> Any:
        """
        Mendapatkan metadata kop (header) Surat Kerja (SK) untuk dokumen laporan tercetak/PDF,
        seperti nomor, judul, lokasi, periode, PM, dan Ketua.

        Args:
            plan_id (UUID | str): ID Surat Kerja (plan).

        Returns:
            Any: Data header dokumen laporan.
        """
        # Melakukan JOIN dengan tabel employee (untuk PM dan Leader) dan unit bisnis
        # untuk membentuk kop surat yang memuat semua informasi proyek
        return await self.fetchone(
            """
            SELECT wp.number, wp.title, wp.location_text, wp.category, bu.name AS unit_name,
                   lower(wp.period) AS period_start, upper(wp.period) - 1 AS period_end,
                   pm.full_name AS pm_name, ld.full_name AS leader_name
            FROM vms.work_plan wp
            LEFT JOIN vms.business_unit bu ON bu.id = wp.unit_id
            LEFT JOIN vms.employee pm ON pm.id = wp.pm_employee_id
            LEFT JOIN vms.employee ld ON ld.id = wp.leader_employee_id
            WHERE wp.id = :plan
            """,
            {"plan": plan_id})

    async def daily_report_doc(self, day_id: UUID | str) -> Any:
        """
        Mengambil keseluruhan isi laporan harian (PM/Ketua) untuk hari tertentu, termasuk detail peninjau,
        daftar lampiran bukti, serta sub-tugas pada hari tersebut.
        Data ini digunakan untuk menghasilkan dokumen laporan.

        Args:
            day_id (UUID | str): ID hari kerja.

        Returns:
            Any: Data laporan harian lengkap beserta array bukti (evidence) dan tugas (tasks).
        """
        # Mengambil data daily_report, men-JOIN pengirim dan pemeriksa (reviewer)
        # Serta menyusun array nama file bukti (evidence) dan daftar tugas (tasks) hari itu
        return await self.fetchone(
            """
            SELECT d.work_date, d.title AS day_title, CAST(r.status AS text) AS status, r.body, r.obstacle,
                   r.resubmitted, r.submitted_at, r.reviewed_at, r.review_note,
                   se.full_name AS submitted_by_name, re.full_name AS reviewed_by_name,
                   COALESCE(ARRAY(SELECT f.file_name FROM vms.report_evidence ev
                                  JOIN vms.file_object f ON f.id = ev.file_id
                                  WHERE ev.daily_report_id = r.id ORDER BY f.file_name), '{}') AS evidence,
                   COALESCE(ARRAY(SELECT t.title FROM vms.work_plan_task t WHERE t.work_plan_day_id = d.id
                                  ORDER BY t.sort_order), '{}') AS tasks
            FROM vms.work_plan_day d
            JOIN vms.daily_report r ON r.work_plan_day_id = d.id
            LEFT JOIN vms.employee se ON se.id = r.submitted_by
            LEFT JOIN vms.employee re ON re.id = r.reviewed_by
            WHERE d.id = :day
            """,
            {"day": day_id})

    async def weekly_report_doc(self, plan_id: UUID | str, name: str) -> Any:
        """
        Mengambil laporan mingguan dari sebuah Surat Kerja berdasarkan namanya (misal 'Minggu 1'),
        lengkap dengan rentang periode dan nama peninjau, untuk dirender ke dokumen.

        Args:
            plan_id (UUID | str): ID rencana kerja.
            name (str): Nama laporan mingguan.

        Returns:
            Any: Data laporan mingguan lengkap.
        """
        # Mengambil detail laporan mingguan dengan mengurai rentang (range) covered_period menjadi start dan end.
        return await self.fetchone(
            """
            SELECT wr.name, lower(wr.covered_period) AS starts_on, upper(wr.covered_period) - 1 AS ends_on,
                   CAST(wr.status AS text) AS status, wr.body, wr.obstacle, wr.resubmitted, wr.review_note,
                   se.full_name AS submitted_by_name, re.full_name AS reviewed_by_name
            FROM vms.weekly_report wr
            LEFT JOIN vms.employee se ON se.id = wr.submitted_by
            LEFT JOIN vms.employee re ON re.id = wr.reviewed_by
            WHERE wr.work_plan_id = :plan AND wr.name = :name
            """,
            {"plan": plan_id, "name": name})
