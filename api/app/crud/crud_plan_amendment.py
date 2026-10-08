"""
app/crud/crud_plan_amendment.py
Adendum saat SK Berjalan (alur SK v2 PR3, flowchart SK2-E): perubahan isi SK yang sedang berjalan tanpa
menyentuh hari yang laporannya sudah dikirim/disetujui, serta daftar usulan perubahan SK.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDPlanAmendment(CRUDBase):
    """
    Kelas CRUD untuk mengelola usulan adendum/perubahan SK (Work Plan).
    """

    async def list_changes(self, plan_id: UUID | str) -> list[Any]:
        """Mengambil daftar usulan perubahan (amendments) pada SK.

        Args:
            plan_id (UUID | str): ID Work Plan.

        Returns:
            list[Any]: Daftar baris riwayat perubahan pada SK tersebut.
        """
        # Melakukan JOIN pada tabel vms.plan_change dengan vms.employee untuk
        # mendapatkan nama lengkap perequest (requested_by) dan pemutus (decided_by).
        return list(await self.fetchall(
            """
            SELECT c.id, CAST(c.change_type AS text) AS change_type, CAST(c.status AS text) AS status, c.reason,
                   c.decision_reason, c.created_at, rq.full_name AS requested_by_name, dc.full_name AS decided_by_name,
                   c.document_id
            FROM vms.plan_change c
            LEFT JOIN vms.employee rq ON rq.id = c.requested_by
            LEFT JOIN vms.employee dc ON dc.id = c.decided_by
            WHERE c.work_plan_id = :plan
            ORDER BY c.created_at DESC
            """,
            {"plan": plan_id},
        ))

    async def update_header(self, plan_id: UUID | str, *, title: str, description: str, category: str,
                            site_id: str, location_text: str, period_start: date, period_end: date,
                            is_out_of_town: bool = False) -> None:
        """Memperbarui informasi header/dasar dari SK.

        Args:
            plan_id (UUID | str): ID Work Plan.
            title (str): Judul baru.
            description (str): Deskripsi baru.
            category (str): Kategori baru.
            site_id (str): ID site (lokasi) baru.
            location_text (str): Teks lokasi baru.
            period_start (date): Tanggal mulai baru.
            period_end (date): Tanggal selesai baru.

        Returns:
            None
        """
        # Memperbarui baris vms.work_plan dengan parameter terbaru.
        # Kolom period diatur ulang menggunakan fungsi daterange().
        # Row_version ditambahkan 1 untuk menjaga konkurensi (optimistic locking).
        await self.execute(
            """
            UPDATE vms.work_plan
               SET title = :title, description = :desc, category = :category, site_id = CAST(:site AS uuid),
                   location_text = :loc, period = daterange(:start, :end, '[]'), is_out_of_town = :oot,
                   row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "title": title, "desc": description, "category": category, "site": site_id,
             "loc": location_text, "start": period_start, "end": period_end, "oot": is_out_of_town},
        )

    async def days_with_report_state(self, plan_id: UUID | str) -> list[Any]:
        """Hari SK beserta status laporannya — hari yang laporannya sudah dikirim/disetujui terkunci.

        Args:
            plan_id (UUID | str): ID Work Plan.

        Returns:
            list[Any]: Daftar hari kerja beserta status daily report (jika ada).
        """
        # Melakukan LEFT JOIN antara vms.work_plan_day (d) dengan vms.daily_report (r)
        # agar hari yang belum dilaporkan juga terambil.
        # Subquery EXISTS mendeteksi apakah ada member_daily_report (laporan harian anggota).
        return list(await self.fetchall(
            """
            SELECT d.id, d.work_date, CAST(r.status AS text) AS report_status,
                   EXISTS (SELECT 1 FROM vms.member_daily_report m WHERE m.work_plan_day_id = d.id) AS has_member_reports
            FROM vms.work_plan_day d LEFT JOIN vms.daily_report r ON r.work_plan_day_id = d.id
            WHERE d.work_plan_id = :plan
            """,
            {"plan": plan_id},
        ))

    async def delete_day(self, day_id: UUID | str) -> None:
        """Menghapus hari kerja dari Work Plan (SK).

        Args:
            day_id (UUID | str): ID dari hari kerja (work_plan_day).
        """
        # Menghapus entri hari kerja dari tabel vms.work_plan_day.
        await self.execute("DELETE FROM vms.work_plan_day WHERE id = :day", {"day": day_id})

    async def clear_tasks(self, day_id: UUID | str, title: str) -> None:
        """Menghapus semua tugas (tasks) pada suatu hari kerja dan memperbarui judul hari tersebut.

        Args:
            day_id (UUID | str): ID dari hari kerja.
            title (str): Judul baru untuk hari kerja.
        """
        # Menghapus semua tugas terkait terlebih dahulu (DELETE)
        # kemudian meng-update judul hari (UPDATE) pada vms.work_plan_day.
        await self.execute("DELETE FROM vms.work_plan_task WHERE work_plan_day_id = :day", {"day": day_id})
        await self.execute("UPDATE vms.work_plan_day SET title = :title WHERE id = :day", {"day": day_id, "title": title})

    async def open_members(self, plan_id: UUID | str) -> list[Any]:
        """Mengambil anggota Work Plan yang aktif (valid_period belum tertutup).

        Args:
            plan_id (UUID | str): ID Work Plan.

        Returns:
            list[Any]: Daftar anggota dengan peran masing-masing.
        """
        # Fungsi upper_inf() digunakan pada PostgreSQL untuk mengecek
        # apakah range batas atas (upper bound) pada kolom valid_period bernilai tak terhingga (infinity).
        # Mengembalikan anggota yang masih aktif (belum dikeluarkan).
        return list(await self.fetchall(
            """
            SELECT CAST(employee_id AS text) AS employee_id, CAST(role_in_plan AS text) AS role_in_plan
            FROM vms.work_plan_member WHERE work_plan_id = :plan AND upper_inf(valid_period)
            """,
            {"plan": plan_id},
        ))

    async def close_member(self, plan_id: UUID | str, employee_id: str, on: date) -> None:
        """Anggota dikeluarkan lewat adendum: baris lama ditutup (riwayat tetap), bukan dihapus.

        Args:
            plan_id (UUID | str): ID Work Plan.
            employee_id (str): ID Karyawan.
            on (date): Tanggal pemberhentian (batas rentang).
        """
        # Menutup rentang waktu keterlibatan anggota dalam SK tanpa mendelete (soft history record).
        # Batas akhir dari daterange (valid_period) akan diubah ke nilai GREATEST antara batas awal + 1
        # dan tanggal (:on) yang dijadwalkan, serta menyimpan reason penghentian.
        await self.execute(
            """
            UPDATE vms.work_plan_member
               SET valid_period = daterange(lower(valid_period), GREATEST(lower(valid_period) + 1, CAST(:on AS date))),
                   removed_reason = 'Adendum SK'
             WHERE work_plan_id = :plan AND employee_id = CAST(:emp AS uuid) AND upper_inf(valid_period)
            """,
            {"plan": plan_id, "emp": employee_id, "on": on},
        )

    async def allocated_asset_ids(self, plan_id: UUID | str) -> set[str]:
        """Mendapatkan daftar ID aset yang sedang dialokasikan dan belum dikembalikan.

        Args:
            plan_id (UUID | str): ID Work Plan.

        Returns:
            set[str]: Himpunan ID aset.
        """
        # Menarik asset_id dari tabel vms.asset_allocation untuk SK tertentu
        # yang masih dialokasikan dan belum dirilis (released_at IS NULL).
        rows = await self.fetchall(
            "SELECT CAST(asset_id AS text) AS asset_id FROM vms.asset_allocation "
            "WHERE work_plan_id = :plan AND released_at IS NULL",
            {"plan": plan_id})
        return {str(r.asset_id) for r in rows}

    async def supersede_effective(self, plan_id: UUID | str, keep_document_id: UUID | str | None) -> None:
        """Versi SK yang lama menjadi Tidak berlaku (adendum diterima / pekerjaan selesai).

        Args:
            plan_id (UUID | str): ID Work Plan.
            keep_document_id (UUID | str | None): ID dokumen SK yang ingin dipertahankan status EFFECTIVE-nya, jika ada.
        """
        # Melakukan update status 'SUPERSEDED' (usang) pada plan_document.
        # Klausa WHERE memastikan hanya dokumen yang dulunya 'EFFECTIVE' yang diubah.
        # Pengecualian diberikan jika id dokumen tersebut merupakan keep_document_id.
        await self.execute(
            """
            UPDATE vms.plan_document SET status = 'SUPERSEDED'
             WHERE work_plan_id = :plan AND status = 'EFFECTIVE'
               AND (CAST(:keep AS uuid) IS NULL OR id <> CAST(:keep AS uuid))
            """,
            {"plan": plan_id, "keep": str(keep_document_id) if keep_document_id else None},
        )

    async def set_revision(self, plan_id: UUID | str, revision: int) -> None:
        """Memperbarui nomor revisi dari Work Plan (SK) beserta row_version.

        Args:
            plan_id (UUID | str): ID Work Plan.
            revision (int): Nomor revisi terbaru.
        """
        # Mengupdate nomor revisi dan menaikkan row_version untuk optimistic locking
        await self.execute("UPDATE vms.work_plan SET revision = :rev, row_version = row_version + 1 WHERE id = :plan",
                           {"plan": plan_id, "rev": revision})

    async def unreturned_assets(self, plan_id: UUID | str) -> list[str]:
        """Aset SK yang belum diajukan pengembaliannya (masih dipesan/dipakai).

        Args:
            plan_id (UUID | str): ID Work Plan.

        Returns:
            list[str]: Daftar nama-nama aset yang belum dikembalikan.
        """
        # Melakukan INNER JOIN ke vms.asset untuk memeriksa status fisik aset (RESERVED/IN_USE).
        # Kolom released_at IS NULL menjamin bahwa alokasi aset pada SK tersebut masih berjalan.
        rows = await self.fetchall(
            """
            SELECT a.name FROM vms.asset_allocation al JOIN vms.asset a ON a.id = al.asset_id
            WHERE al.work_plan_id = :plan AND al.released_at IS NULL AND a.status IN ('RESERVED', 'IN_USE')
            ORDER BY a.name
            """,
            {"plan": plan_id})
        return [str(r.name) for r in rows]
