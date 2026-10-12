"""
app/crud/crud_plan_change.py
Usulan perubahan SK — perpanjangan & personel (V-22). SQL saja; aturan di
services/plan_change_service.py. Dokumen adendum ditulis ke `plan_document` (isi terkunci, R4).
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from app.core.enums import ChangeStatus, ChangeType, DocumentKind, DocumentStatus

from .base import CRUDBase

# domain.js makeDay — hari baru dari perpanjangan
_DAY_TITLES = ("Persiapan & survei lokasi", "Instalasi & konfigurasi", "Pengujian & serah terima")
_DAY_TASKS = ("Briefing keselamatan dan pemeriksaan area", "Pelaksanaan pekerjaan sesuai rencana")


class CRUDPlanChange(CRUDBase):
    """
    Kelas CRUD untuk memproses usulan perubahan (adendum) pada Work Plan (SK), baik
    berupa perpanjangan waktu maupun pergantian personel.
    """

    async def employee_of(self, user_id: UUID | str) -> Any:
        """Mengambil ID Karyawan (employee_id) dari seorang pengguna.

        Args:
            user_id (UUID | str): ID dari pengguna (app_user).

        Returns:
            Any: ID Karyawan dalam bentuk string.
        """
        # Melakukan scalar query pada tabel vms.app_user
        return await self.scalar("SELECT employee_id::text FROM vms.app_user WHERE id = :uid", {"uid": user_id})

    async def get_change(self, change_id: UUID | str) -> Any:
        """Mengambil rincian data usulan perubahan (plan_change).

        Args:
            change_id (UUID | str): ID usulan perubahan.

        Returns:
            Any: Baris data usulan perubahan.
        """
        # Mengeksekusi SELECT tunggal ke tabel vms.plan_change
        return await self.fetchone(
            """
            SELECT id, work_plan_id, CAST(change_type AS text) AS change_type, CAST(status AS text) AS status,
                   reason, decision_reason
            FROM vms.plan_change WHERE id = :id
            """,
            {"id": change_id},
        )

    async def open_change(self, plan_id: UUID | str) -> Any:
        """Memeriksa apakah ada usulan perubahan yang masih terbuka (belum final) pada suatu SK.

        Args:
            plan_id (UUID | str): ID Work Plan.

        Returns:
            Any: ID perubahan jika ada yang berstatus PENDING_PM atau AWAITING_LEADER_ACCEPTANCE.
        """
        # Memastikan tidak ada overlapping usulan perubahan
        return await self.scalar(
            """
            SELECT id FROM vms.plan_change
            WHERE work_plan_id = :plan AND status IN ('PENDING_PM', 'AWAITING_LEADER_ACCEPTANCE')
            """,
            {"plan": plan_id},
        )

    async def lock_change(self, change_id: UUID | str, org_id: UUID | str) -> Any:
        """Usulan + SK-nya (dikunci). None bila tidak ada / organisasi lain.

        Args:
            change_id (UUID | str): ID usulan perubahan.
            org_id (UUID | str): ID organisasi untuk validasi.

        Returns:
            Any: Baris data perubahan beserta SK-nya, dalam keadaan terkunci (locked).
        """
        # Menggunakan FOR UPDATE OF c, wp untuk melakukan row-level locking
        # agar konkurensi (race condition) bisa dicegah selama proses persetujuan.
        return await self.fetchone(
            """
            SELECT c.id, c.work_plan_id, c.change_type, c.status, c.reason, c.base_revision, c.proposed_revision,
                   upper(c.new_period) - 1 AS new_period_end, c.proposed_leader_id::text AS proposed_leader_id,
                   c.proposed_members, c.document_id, wp.revision AS plan_revision, wp.status AS plan_status,
                   lower(wp.period) AS period_start, upper(wp.period) - 1 AS period_end
            FROM vms.plan_change c JOIN vms.work_plan wp ON wp.id = c.work_plan_id
            WHERE c.id = :id AND wp.organization_id = CAST(:org AS uuid) AND wp.deleted_at IS NULL
            FOR UPDATE OF c, wp
            """,
            {"id": change_id, "org": org_id},
        )

    async def next_document_version(self, plan_id: UUID | str) -> int:
        """Menghitung versi dokumen adendum berikutnya untuk sebuah SK.

        Args:
            plan_id (UUID | str): ID Work Plan.

        Returns:
            int: Nomor versi dokumen berikutnya.
        """
        # Mengkalkulasi nilai GREATEST antara revisi SK (wp.revision)
        # dengan versi tertinggi dari dokumen SK yang sudah ada sebelumnya (max(d.version)).
        return int(await self.scalar(
            """
            SELECT GREATEST(wp.revision, COALESCE(max(d.version), 0)) + 1
            FROM vms.work_plan wp LEFT JOIN vms.plan_document d ON d.work_plan_id = wp.id
            WHERE wp.id = :plan GROUP BY wp.revision
            """,
            {"plan": plan_id},
        ))

    async def insert_change(self, *, plan_id: UUID | str, change_type: ChangeType, status: ChangeStatus,
                            reason: str, base_revision: int, proposed_revision: int, requested_by: str,
                            old_end: date | None = None, new_end: date | None = None,
                            leader_id: str | None = None, member_ids: list[str] | None = None) -> Any:
        """Memasukkan usulan perubahan baru (plan_change) ke dalam database.

        Args:
            plan_id (UUID | str): ID Work Plan.
            change_type (ChangeType): Tipe perubahan (waktu atau personel).
            status (ChangeStatus): Status persetujuan perubahan.
            reason (str): Alasan perubahan.
            base_revision (int): Versi revisi sebelum diubah.
            proposed_revision (int): Versi revisi yang diusulkan.
            requested_by (str): ID Karyawan yang mengusulkan.
            old_end (date | None): Tanggal selesai sebelumnya.
            new_end (date | None): Tanggal selesai baru yang diusulkan.
            leader_id (str | None): ID Ketua yang diusulkan.
            member_ids (list[str] | None): Daftar ID Anggota yang diusulkan.

        Returns:
            Any: ID dari baris perubahan yang baru dimasukkan.
        """
        # Melakukan penyisipan ke tabel vms.plan_change dan memformat tanggal (daterange).
        return await self.scalar(
            """
            INSERT INTO vms.plan_change (
                work_plan_id, change_type, status, reason, old_period, new_period,
                proposed_leader_id, proposed_members, base_revision, proposed_revision, requested_by
            ) VALUES (
                :plan, CAST(:type AS vms.change_type), CAST(:status AS vms.change_status), :reason,
                CASE WHEN CAST(:old_end AS date) IS NULL THEN NULL
                     ELSE daterange(NULL, CAST(:old_end AS date) + 1, '[)') END,
                CASE WHEN CAST(:new_end AS date) IS NULL THEN NULL
                     ELSE daterange(NULL, CAST(:new_end AS date) + 1, '[)') END,
                CAST(:leader AS uuid), CAST(:members AS uuid[]), :base, :proposed, :by
            ) RETURNING id
            """,
            {"plan": plan_id, "type": change_type, "status": status, "reason": reason, "old_end": old_end,
             "new_end": new_end, "leader": leader_id, "members": member_ids or [], "base": base_revision,
             "proposed": proposed_revision, "by": requested_by},
        )

    async def issue_addendum(self, change_id: UUID | str, plan_id: UUID | str, kind: DocumentKind, version: int,
                             snapshot: dict[str, Any], issued_by: str, reason: str) -> None:
        """Dokumen adendum menunggu penerimaan; nomor = nomor SK + /ADD-n (domain.js).

        Args:
            change_id (UUID | str): ID usulan perubahan (plan_change).
            plan_id (UUID | str): ID Work Plan.
            kind (DocumentKind): Jenis dokumen.
            version (int): Versi dokumen.
            snapshot (dict[str, Any]): Rekaman data SK saat itu (JSON).
            issued_by (str): Penerbit dokumen.
            reason (str): Alasan penerbitan dokumen.

        Returns:
            None
        """
        suffix = "ADD-SDM" if kind == DocumentKind.PERSONNEL_ADDENDUM else "ADD"
        # Memasukkan record ke vms.plan_document dan mengaitkannya ke vms.plan_change.
        # Menghasilkan nomor surat dengan memanipulasi string menggunakan suffix dan version.
        document_id = await self.scalar(
            """
            INSERT INTO vms.plan_document (work_plan_id, kind, version, number, status, snapshot, snapshot_sha256,
                                           reason, issued_by)
            SELECT id, CAST(:kind AS vms.document_kind), :version, number || '/' || :suffix || '-' || (:version - 1),
                   CAST(:awaiting AS vms.document_status), CAST(:snapshot AS jsonb), ''::bytea, :reason, :issued_by
            FROM vms.work_plan WHERE id = :plan
            RETURNING id
            """,
            {"plan": plan_id, "kind": kind, "version": version, "suffix": suffix, "reason": reason,
             "awaiting": DocumentStatus.AWAITING_ACCEPTANCE, "snapshot": json.dumps(snapshot, default=str),
             "issued_by": issued_by},
        )
        await self.execute("UPDATE vms.plan_change SET document_id = :doc WHERE id = :id",
                           {"doc": document_id, "id": change_id})

    async def pending_amendment_ids(self, plan_id: UUID | str) -> list[str]:
        """Permintaan revisi ketua yang masih menunggu PM pada rencana kerja ini (terlama dulu)."""
        rows = await self.fetchall(
            "SELECT id FROM vms.plan_change WHERE work_plan_id = CAST(:plan AS uuid) "
            "AND change_type = 'AMENDMENT' AND status = 'PENDING_PM' ORDER BY created_at", {"plan": str(plan_id)})
        return [str(r.id) for r in rows]

    async def set_change(self, change_id: UUID | str, status: ChangeStatus, decided_by: str | None = None,
                         decision_reason: str | None = None) -> None:
        """Menetapkan status keputusan (disetujui/ditolak) pada suatu usulan perubahan.

        Args:
            change_id (UUID | str): ID perubahan.
            status (ChangeStatus): Status baru.
            decided_by (str | None): ID Karyawan yang memutuskan.
            decision_reason (str | None): Alasan atas keputusan.
        """
        # Melakukan UPDATE pada tabel vms.plan_change.
        # Fungsi COALESCE memastikan nilai yang ada tidak tertimpa NULL apabila parameter bernilai None.
        await self.execute(
            """
            UPDATE vms.plan_change
               SET status = CAST(:status AS vms.change_status),
                   decided_by = COALESCE(CAST(:by AS uuid), decided_by),
                   decision_reason = COALESCE(:reason, decision_reason)
             WHERE id = :id
            """,
            {"id": change_id, "status": status, "by": decided_by, "reason": decision_reason},
        )

    async def set_document(self, document_id: UUID | str | None, status: DocumentStatus,
                           accepted_by: str | None = None) -> None:
        """Membaharui status dari sebuah dokumen (misal: telah disetujui).

        Args:
            document_id (UUID | str | None): ID Dokumen.
            status (DocumentStatus): Status baru dari dokumen.
            accepted_by (str | None): ID pegawai yang menerima/menyetujui.
        """
        if document_id is None:
            return
        # Melakukan UPDATE status dokumen di tabel vms.plan_document.
        # Merekam kolom accepted_by dan waktu penerimaan accepted_at.
        await self.execute(
            """
            UPDATE vms.plan_document
               SET status = CAST(:status AS vms.document_status),
                   accepted_by = COALESCE(accepted_by, CAST(:by AS uuid)),
                   accepted_at = CASE WHEN CAST(:by AS uuid) IS NULL THEN accepted_at ELSE COALESCE(accepted_at, now()) END
             WHERE id = :id
            """,
            {"id": document_id, "status": status, "by": accepted_by},
        )

    async def apply_extension(self, plan_id: UUID | str, old_end: date, new_end: date, revision: int) -> None:
        """Periode diperpanjang, revisi naik, hari baru dibuat (domain.js ACCEPT_CHANGE + makeDay).

        Args:
            plan_id (UUID | str): ID Work Plan.
            old_end (date): Tanggal selesai sebelumnya.
            new_end (date): Tanggal selesai yang baru.
            revision (int): Nomor revisi.
        """
        # Melakukan pembaruan batas akhir periode pada Work Plan.
        # Kolom period di-set menggunakan daterange yang terbuka kanan '[)' pada batas atasnya.
        await self.execute(
            """
            UPDATE vms.work_plan
               SET period = daterange(lower(period), CAST(:new_end AS date) + 1, '[)'),
                   revision = :revision, row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "new_end": new_end, "revision": revision},
        )
        existing = int(await self.scalar("SELECT count(*) FROM vms.work_plan_day WHERE work_plan_id = :plan",
                                         {"plan": plan_id}))
        day = old_end + timedelta(days=1)
        index = existing
        while day <= new_end:
            # Memasukkan iterasi hari kerja baru (work_plan_day) dan tugas dasarnya (work_plan_task).
            day_id = await self.scalar(
                """
                INSERT INTO vms.work_plan_day (work_plan_id, work_date, title, sort_order)
                VALUES (:plan, :day, :title, :sort)
                ON CONFLICT (work_plan_id, work_date) DO NOTHING
                RETURNING id
                """,
                {"plan": plan_id, "day": day, "title": _DAY_TITLES[index % 3], "sort": index},
            )
            if day_id is not None and _DAY_TASKS:
                await self.execute(
                    """
                    INSERT INTO vms.work_plan_task (work_plan_day_id, title, sort_order)
                    SELECT :day, unnest(CAST(:titles AS text[])), unnest(CAST(:sorts AS int[]))
                    """,
                    {"day": day_id, "titles": _DAY_TASKS, "sorts": list(range(len(_DAY_TASKS)))}
                )
            day += timedelta(days=1)
            index += 1

    async def apply_personnel(self, plan_id: UUID | str, leader_id: str, member_ids: list[str],
                              revision: int) -> None:
        """Susunan baru berlaku mulai hari ini menurut zona waktu organisasi: baris yang tidak lagi
        sesuai ditutup (bukan dihapus — riwayat tetap), baris baru dibuka, ketua di SK diganti.

        Args:
            plan_id (UUID | str): ID Work Plan.
            leader_id (str): ID Karyawan yang menjadi ketua baru.
            member_ids (list[str]): Daftar anggota.
            revision (int): Nomor revisi.
        """
        wanted = [(leader_id, "LEADER")] + [(m, "MEMBER") for m in member_ids]
        # Mengakhiri penugasan bagi anggota lama yang sudah tidak berada di daftar baru (wanted).
        # Penetapan batas akhir menggunakan waktu lokal (timezone) yang berjalan pada hari ini.
        await self.execute(
            """
            WITH effective AS (
                SELECT GREATEST(lower(wp.period), (now() AT TIME ZONE o.timezone)::date) AS day
                FROM vms.work_plan wp JOIN vms.organization o ON o.id = wp.organization_id WHERE wp.id = :plan
            )
            UPDATE vms.work_plan_member AS m
               SET valid_period = daterange(lower(m.valid_period), GREATEST(lower(m.valid_period), effective.day), '[)')
              FROM effective
             WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)
               AND (m.employee_id, CAST(m.role_in_plan AS text)) NOT IN (
                   SELECT CAST(e AS uuid), r FROM unnest(CAST(:emps AS text[]), CAST(:roles AS text[])) AS w(e, r))
            """,
            {"plan": plan_id, "emps": [e for e, _ in wanted], "roles": [r for _, r in wanted]},
        )
        if wanted:
            # Memasukkan baris (record) anggota-anggota baru yang belum ada di dalam database
            # dan men-set awal masa berlaku (valid_period) ke waktu lokal hari ini (timezone dependent).
            await self.execute(
                """
                INSERT INTO vms.work_plan_member (work_plan_id, employee_id, role_in_plan, valid_period)
                SELECT wp.id, CAST(u.emp AS uuid), CAST(u.role AS vms.role_code),
                       daterange(GREATEST(lower(wp.period), (now() AT TIME ZONE o.timezone)::date), NULL, '[)')
                FROM vms.work_plan wp
                JOIN vms.organization o ON o.id = wp.organization_id
                CROSS JOIN unnest(CAST(:emps AS text[]), CAST(:roles AS text[])) AS u(emp, role)
                WHERE wp.id = :plan AND NOT EXISTS (
                    SELECT 1 FROM vms.work_plan_member m
                    WHERE m.work_plan_id = wp.id AND m.employee_id = CAST(u.emp AS uuid)
                      AND m.role_in_plan = CAST(u.role AS vms.role_code) AND upper_inf(m.valid_period))
                """,
                {"plan": plan_id, "emps": [str(e) for e, _ in wanted], "roles": [r for _, r in wanted]}
            )
        # Menetapkan siapa ID ketua tim yang baru pada kolom leader_employee_id,
        # serta memperbarui status revisi dari Work Plan.
        await self.execute(
            """
            UPDATE vms.work_plan SET leader_employee_id = CAST(:leader AS uuid), revision = :revision,
                   row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "leader": leader_id, "revision": revision},
        )
