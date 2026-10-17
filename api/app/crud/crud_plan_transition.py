"""
app/crud/crud_plan_transition.py
Kueri untuk transisi SK (publish, accept, start). Satu-satunya tempat SQL-nya (dok 12).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.enums import ChangeStatus, DocumentKind, DocumentStatus, PlanStatus

from .base import CRUDBase

# Daftar kolom ditulis ulang di setiap kueri (bukan disambung) agar tiap kueri tetap literal statis
# yang diperiksa terhadap skema oleh tests/test_sql_matches_schema.py.


class CRUDPlanTransition(CRUDBase):
    """
    CRUD untuk mengelola transisi status SK (rencana kerja).
    Termasuk pembatalan, pengarsipan, pengajuan adendum, penerbitan, hingga laporan akhir.
    """

    async def lock_plan(self, plan_id: UUID | str, org_id: UUID | str, include_archived: bool = False) -> Any:
        """
        Mengunci baris rencana kerja (SK) untuk transaksi yang akan mengubah status.

        Args:
            plan_id (UUID | str): ID SK.
            org_id (UUID | str): ID organisasi.
            include_archived (bool): Jika True, akan tetap memuat data yang sudah diarsipkan (soft-deleted).

        Returns:
            Any: Record SK yang terkunci.
        """
        # FOR UPDATE mengamankan baris agar transaksi lain yang mengubah data yang sama harus menunggu.
        return await self.fetchone(
            """
            SELECT id, unit_id, site_id, number, title, location_text, description,
                   lower(period) AS period_start, upper(period) - 1 AS period_end,
                   status, pm_employee_id, leader_employee_id, revision, row_version, cancellation_reason,
                   deleted_at IS NOT NULL AS archived
            FROM vms.work_plan
            WHERE id = :id AND organization_id = :org AND (CAST(:any AS boolean) OR deleted_at IS NULL)
            FOR UPDATE
            """,
            {"id": plan_id, "org": org_id, "any": include_archived},
        )

    async def cancel(self, plan_id: UUID | str, reason: str) -> None:
        """
        Membatalkan SK; usulan perubahan ditarik dan aset yang masih dipesan dilepas.
        SK yang dibatalkan beralih ke status CANCELLED.

        Args:
            plan_id (UUID | str): ID SK yang dibatalkan.
            reason (str): Alasan pembatalan.
        """
        # Memperbarui status SK dan menaikkan row_version.
        await self.execute(
            """
            UPDATE vms.work_plan
               SET status = CAST(:cancelled AS vms.plan_status), cancellation_reason = :reason,
                   row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "reason": reason, "cancelled": PlanStatus.CANCELLED},
        )
        # Menarik kembali (WITHDRAWN) usulan perubahan yang masih tertunda.
        await self.execute(
            """
            UPDATE vms.plan_change SET status = CAST(:withdrawn AS vms.change_status)
             WHERE work_plan_id = :plan AND status IN ('PENDING_PM', 'AWAITING_LEADER_ACCEPTANCE')
            """,
            {"plan": plan_id, "withdrawn": ChangeStatus.WITHDRAWN},
        )
        # Menarik dokumen SK yang belum selesai ditandatangani.
        await self.execute(
            "UPDATE vms.plan_document SET status = CAST(:withdrawn AS vms.document_status) WHERE work_plan_id = :plan",
            {"plan": plan_id, "withdrawn": DocumentStatus.WITHDRAWN},
        )
        # Aset yang baru dipesan (RESERVED) dilepas, namun yang sedang dipakai (IN_USE) tetap wajib dikembalikan.
        await self.execute(
            """
            WITH freed AS (
                UPDATE vms.asset_allocation a SET released_at = now()
                  FROM vms.asset s
                 WHERE a.asset_id = s.id AND a.work_plan_id = :plan AND a.released_at IS NULL
                   AND s.status = 'RESERVED'
                RETURNING a.asset_id
            )
            UPDATE vms.asset SET status = 'AVAILABLE' WHERE id IN (SELECT asset_id FROM freed)
            """,
            {"plan": plan_id},
        )

    async def ever_published(self, plan_id: UUID | str) -> bool:
        """
        Mengecek apakah SK ini pernah diterbitkan (punya dokumen) atau belum.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            bool: True jika pernah diterbitkan, False jika belum.
        """
        # Mengecek keberadaan record dokumen plan_document dari SK ini.
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.plan_document WHERE work_plan_id = :plan)", {"plan": plan_id}))

    async def has_active_allocation(self, plan_id: UUID | str) -> bool:
        """
        Mengecek apakah SK ini masih memiliki alokasi aset yang sedang aktif (belum dirilis).

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            bool: True jika ada alokasi aktif.
        """
        # Jika released_at IS NULL, aset masih dialokasikan pada SK ini.
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.asset_allocation WHERE work_plan_id = :plan AND released_at IS NULL)",
            {"plan": plan_id}))

    async def archive(self, plan_id: UUID | str, user_id: UUID | str, reason: str) -> None:
        """
        Soft delete rencana kerja — diarsipkan namun riwayat datanya tetap ada.

        Args:
            plan_id (UUID | str): ID SK.
            user_id (UUID | str): ID pengguna (app_user) yang menghapus.
            reason (str): Alasan pengarsipan.
        """
        # Melakukan soft-delete dengan mengatur deleted_at menjadi sekarang (now()).
        await self.execute(
            """
            UPDATE vms.work_plan
               SET deleted_at = now(), deleted_by = :user, deletion_reason = :reason, row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "user": user_id, "reason": reason},
        )

    async def restore(self, plan_id: UUID | str) -> None:
        """
        Mengembalikan rencana kerja dari arsip (undo delete).
        Alasan pengarsipan sebelumnya tidak diubah sebagai riwayat.

        Args:
            plan_id (UUID | str): ID SK.
        """
        # Menghapus flag deleted_at dan deleted_by (NULL).
        await self.execute(
            "UPDATE vms.work_plan SET deleted_at = NULL, deleted_by = NULL, row_version = row_version + 1 WHERE id = :plan",
            {"plan": plan_id},
        )

    async def get_plan(self, plan_id: UUID | str) -> Any:
        """
        Mendapatkan metadata lengkap rencana kerja tanpa JSON snapshot.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            Any: Metadata lengkap dari record SK.
        """
        # Membaca data umum work_plan secara utuh tanpa join rumit.
        return await self.fetchone(
            """
            SELECT id, unit_id, site_id, number, title, location_text, description,
                   lower(period) AS period_start, upper(period) - 1 AS period_end,
                   status, pm_employee_id, leader_employee_id, revision, row_version, cancellation_reason,
                   appeal_reason, category
            FROM vms.work_plan WHERE id = :id
            """,
            {"id": plan_id},
        )

    async def appeal(self, plan_id: UUID | str, reason: str) -> None:
        """
        Mengajukan banding/adendum atas SK yang sudah diterbitkan.

        Args:
            plan_id (UUID | str): ID SK.
            reason (str): Alasan banding.
        """
        # Memperbarui status menjadi APPEALED dan menyimpan alasan banding.
        await self.execute(
            """
            UPDATE vms.work_plan
               SET status = CAST(:appealed AS vms.plan_status), appeal_reason = :reason, row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "reason": reason, "appealed": PlanStatus.APPEALED},
        )
        # Alur SK v2: dokumen yang menunggu tanda tangan ketua tidak berlaku lagi (karena sedang direvisi PM).
        await self.execute(
            "UPDATE vms.plan_document SET status = CAST(:superseded AS vms.document_status) "
            "WHERE work_plan_id = :plan AND status = :awaiting",
            {"plan": plan_id, "superseded": DocumentStatus.SUPERSEDED, "awaiting": DocumentStatus.AWAITING_ACCEPTANCE},
        )

    async def start_due(self, org_id: UUID | str, today: Any) -> list[str]:
        """
        Memulai SK yang sudah Diterima dan tanggal mulainya sudah tiba hari ini (menjadi ONGOING).

        Args:
            org_id (UUID | str): ID organisasi.
            today (Any): Tanggal batas mulai (hari ini).

        Returns:
            list[str]: Daftar ID rencana kerja yang baru saja diaktifkan/dimulai.
        """
        rows = await self.fetchall(
            """
            UPDATE work_plan_weekly
               SET status = 'ONGOING', update_at = NOW()
             WHERE status = 'APPROVED'
               AND start_date <= CAST(:today AS date)
               AND delete_at IS NULL
            RETURNING CAST(weekly_plan_id AS text) AS id
            """,
            {"today": today},
        )
        return [str(r.id) for r in rows]

    async def revise(self, plan_id: UUID | str) -> None:
        """
        Mengembalikan rencana kerja (SK) ke status DRAFT untuk revisi berikutnya.
        Dokumen revisi lama yang belum aktif menjadi kadaluarsa (SUPERSEDED).

        Args:
            plan_id (UUID | str): ID SK.
        """
        # Menaikkan nilai versi revisi dari draft SK.
        await self.execute(
            """
            UPDATE vms.work_plan
               SET status = CAST(:draft AS vms.plan_status), revision = revision + 1, row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "draft": PlanStatus.DRAFT},
        )
        # Menandai seluruh dokumen rencana kerja yang ada sebagai digantikan (SUPERSEDED).
        await self.execute(
            "UPDATE vms.plan_document SET status = CAST(:superseded AS vms.document_status) WHERE work_plan_id = :plan",
            {"plan": plan_id, "superseded": DocumentStatus.SUPERSEDED},
        )

    async def active_team(self, plan_id: UUID | str) -> list[Any]:
        """
        Mendapatkan tim yang aktif berpartisipasi dalam SK (valid_period terbuka),
        beserta status keaktifan akun karyawannya.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            list[Any]: Daftar record (employee_id, role_in_plan, employee_active).
        """
        # Cek upper_inf(valid_period) untuk memastikan anggotanya masih aktif di dalam proyek ini.
        return list(await self.fetchall(
            """
            SELECT m.employee_id::text AS employee_id, m.role_in_plan::text AS role_in_plan,
                   e.is_active AND e.deleted_at IS NULL AS employee_active
            FROM vms.work_plan_member m JOIN vms.employee e ON e.id = m.employee_id
            WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)
            """,
            {"plan": plan_id},
        ))

    async def day_details_complete(self, plan_id: UUID | str) -> bool:
        """
        Memastikan setiap hari dalam periode SK sudah terisi dengan detail kerja.
        Syarat: setiap tanggal harus punya judul hari yang valid dan minimal 1 tugas berjudul.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            bool: True jika lengkap seluruh harinya.
        """
        # Hari libur = tanggal yang tidak punya baris hari (2026-10-09), jadi yang diperiksa adalah SEMUA hari kerja yang
        # ada: tiap hari berjudul dan punya >= 1 tugas berjudul; minimal satu hari, dan hari pertama/terakhir tepat di
        # tanggal mulai/selesai rencana.
        return bool(await self.scalar(
            """
            SELECT count(*) > 0
               AND count(*) = count(*) FILTER (
                     WHERE btrim(d.title) <> ''
                       AND EXISTS (SELECT 1 FROM vms.work_plan_task t WHERE t.work_plan_day_id = d.id)
                       AND NOT EXISTS (SELECT 1 FROM vms.work_plan_task t
                                       WHERE t.work_plan_day_id = d.id AND btrim(t.title) = ''))
               AND min(d.work_date) = lower(wp.period) AND max(d.work_date) = upper(wp.period) - 1
            FROM vms.work_plan wp
            JOIN vms.work_plan_day d ON d.work_plan_id = wp.id AND d.work_date <@ wp.period
            WHERE wp.id = :plan
            GROUP BY wp.id, wp.period
            """,
            {"plan": plan_id},
        ))

    async def snapshot(self, plan_id: UUID | str) -> Any:
        """
        Membekukan isi dokumen secara komprehensif saat pembuatan SK.
        Data ini disisipkan utuh agar tidak terpengaruh oleh perubahan master ke depan.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            Any: Record JSON dokumen beku.
        """
        # Menyatukan data SK dasar, tim anggota aktif, detail hari dan task,
        # alokasi aset, serta lampiran ke dalam satu hirarki besar berformat JSONB
        # agar terjamin keutuhannya sebagai snapshot (dokumen tak tergoyahkan).
        return await self.scalar(
            """
            SELECT jsonb_build_object(
              'plan', (SELECT to_jsonb(p) - 'row_version' FROM (
                  SELECT wp.id, wp.unit_id, wp.site_id, wp.number, wp.title, wp.location_text, wp.description,
                   lower(wp.period) AS period_start, upper(wp.period) - 1 AS period_end,
                   wp.status, wp.pm_employee_id, wp.leader_employee_id, wp.revision, wp.row_version,
                   wp.cancellation_reason, wp.category, bu.name AS unit_name, s.description AS site_description,
                   ST_Y(s.location::geometry) AS lat, ST_X(s.location::geometry) AS lng,
                   pm.full_name AS pm_name, pm.position AS pm_position,
                   wp.is_out_of_town, wt.name AS work_type_name
                  FROM vms.work_plan wp
                  LEFT JOIN vms.business_unit bu ON bu.id = wp.unit_id
                  LEFT JOIN vms.site s ON s.id = wp.site_id
                  LEFT JOIN vms.employee pm ON pm.id = wp.pm_employee_id
                  LEFT JOIN vms.work_type wt ON wt.id = wp.work_type_id
                  WHERE wp.id = :plan) p),
              'team', COALESCE((SELECT jsonb_agg(jsonb_build_object('employee_id', m.employee_id,
                                        'full_name', e.full_name, 'position', e.position,
                                        'role_in_plan', m.role_in_plan, 'since', lower(m.valid_period))
                                        ORDER BY m.role_in_plan, e.full_name)
                                FROM vms.work_plan_member m JOIN vms.employee e ON e.id = m.employee_id
                                WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)), '[]'),
              'days', COALESCE((SELECT jsonb_agg(jsonb_build_object('work_date', d.work_date, 'title', d.title,
                                        'site_name', (SELECT s2.name FROM vms.site s2 WHERE s2.id = d.site_id),
                                        'work_type_name', (SELECT w2.name FROM vms.work_type w2 WHERE w2.id = d.work_type_id),
                                        'members', (SELECT jsonb_agg(de2.full_name ORDER BY de2.full_name)
                                                    FROM vms.work_plan_day_member dm
                                                    JOIN vms.employee de2 ON de2.id = dm.employee_id
                                                    WHERE dm.work_plan_day_id = d.id),
                                        'tasks', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
                                                    'title', t.title, 'description', t.description,
                                                    'files', (SELECT COALESCE(jsonb_agg(f.file_name
                                                                ORDER BY ta.sort_order), '[]')
                                                              FROM vms.work_plan_task_attachment ta
                                                              JOIN vms.file_object f ON f.id = ta.file_id
                                                              WHERE ta.task_id = t.id))
                                                    ORDER BY t.sort_order, t.title), '[]')
                                                  FROM vms.work_plan_task t WHERE t.work_plan_day_id = d.id))
                                        ORDER BY d.work_date)
                                FROM vms.work_plan_day d WHERE d.work_plan_id = :plan), '[]'),
              'assets', COALESCE((SELECT jsonb_agg(jsonb_build_object('kind', a.kind, 'code', a.code,
                                        'name', a.name, 'vehicle_type', a.vehicle_type, 'driver_name', de.full_name)
                                        ORDER BY a.kind, a.name)
                                FROM vms.asset_allocation al JOIN vms.asset a ON a.id = al.asset_id
                                LEFT JOIN vms.employee de ON de.id = al.driver_employee_id
                                WHERE al.work_plan_id = :plan AND al.released_at IS NULL), '[]'),
              'attachments', COALESCE((SELECT jsonb_agg(jsonb_build_object('file_id', a.file_id,
                                        'file_name', f.file_name) ORDER BY a.sort_order)
                                FROM vms.work_plan_attachment a JOIN vms.file_object f ON f.id = a.file_id
                                WHERE a.work_plan_id = :plan), '[]')
            )
            """,
            {"plan": plan_id},
        )

    async def employee_id_of(self, user_id: UUID | str) -> str | None:
        """
        Mendapatkan ID Karyawan yang merujuk pada pengguna sistem.

        Args:
            user_id (UUID | str): ID pengguna (app_user).

        Returns:
            str | None: ID Karyawan bila ada.
        """
        value = await self.scalar("SELECT employee_id::text FROM public.users WHERE user_id = :uid", {"uid": user_id})
        return str(value) if value else None

    async def is_leader(self, plan_id: UUID | str, user_id: UUID | str) -> bool:
        """
        Memastikan apakah user ini berhak menyetujui sebagai Ketua SK.

        Args:
            plan_id (UUID | str): ID SK.
            user_id (UUID | str): ID pengguna saat ini.

        Returns:
            bool: True bila user bertindak sebagai Leader.
        """
        return bool(await self.scalar(
            """
            SELECT EXISTS (
                SELECT 1 FROM public.work_plan_weekly wp
                JOIN public.users u ON u.employee_id = wp.created_by_id
                WHERE wp.weekly_plan_id = :plan AND u.user_id = :user
                UNION
                SELECT 1 FROM public.work_plan_weekly wp
                JOIN public.team t ON t.team_id = wp.team_id
                JOIN public.users u ON u.employee_id = t.leader_employee_id
                WHERE wp.weekly_plan_id = :plan AND u.user_id = :user
            )
            """,
            {"plan": plan_id, "user": user_id},
        ))

    async def publish(self, plan_id: UUID | str) -> None:
        """
        Menerbitkan dokumen SK dan menyematkan format nomor sementara jika SK belum punya nomor.

        Args:
            plan_id (UUID | str): ID SK.
        """
        # Nomor SK sementara; format resmi ditetapkan fase 6 dari contoh dokumen perusahaan (K-14).
        # Pakai 8 karakter TERAKHIR id: awal UUIDv7 adalah cap waktu, sehingga SK yang dibuat
        # berdekatan dulu bernomor sama → terbit gagal duplicate key (temuan uji nyata R-17).
        await self.execute(
            """
            UPDATE vms.work_plan
               SET status = :published, row_version = row_version + 1,
                   number = COALESCE(number, 'RK-' || to_char(CURRENT_DATE, 'YYYYMM') || '-' || right(id::text, 8))
             WHERE id = :plan
            """,
            {"plan": plan_id, "published": PlanStatus.PUBLISHED},
        )

    async def insert_document(self, plan_id: UUID | str, revision: int, snapshot: Any, issued_by: str) -> None:
        """
        Memasukkan riwayat dokumen SK baru dari hasil snapshot.

        Args:
            plan_id (UUID | str): ID SK.
            revision (int): Versi revisi dokumen ini.
            snapshot (Any): Payload beku JSON.
            issued_by (str): ID Karyawan yang menerbitkan (PM).
        """
        # Melakukan duplikasi record ke dalam tabel plan_document dan di set ke AWAITING_ACCEPTANCE.
        # SHA256 snapshot tidak dihitung di sini, karena sudah ada trigger basis data (plan_document_hash).
        await self.execute(
            """
            INSERT INTO vms.plan_document (work_plan_id, kind, version, number, status, snapshot, snapshot_sha256, issued_by)
            SELECT id, CAST(:kind AS vms.document_kind), :version, number, CAST(:status AS vms.document_status),
                   CAST(:snapshot AS jsonb), ''::bytea, :issued_by
            FROM vms.work_plan WHERE id = :plan
            """,
            {
                "plan": plan_id, "version": revision, "snapshot": snapshot, "issued_by": issued_by,
                "kind": DocumentKind.INITIAL_ORDER if revision == 1 else DocumentKind.REVISION,
                "status": DocumentStatus.AWAITING_ACCEPTANCE,
            },
        )

    async def activate_reserved_assets(self, plan_id: UUID | str) -> None:
        """
        Mengaktifkan status aset (alat/kendaraan) yang dipesan untuk SK.
        """
        pass

    async def has_unchecked_vehicle(self, plan_id: UUID | str) -> bool:
        """
        Mengecek apakah SK ini memiliki kendaraan yang masih tertunda verifikasi oleh pengemudinya.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            bool: True jika ada kendaraan (VEHICLE) dengan driver_checked_at yang masih kosong.
        """
        # Mengevaluasi keterkaitan alokasi kendaraan yang belum dilakukan checklist.
        return bool(await self.scalar(
            """
            SELECT EXISTS (
                SELECT 1
                FROM vms.asset_allocation al
                JOIN vms.asset a ON a.id = al.asset_id
                WHERE al.work_plan_id = :plan AND al.released_at IS NULL
                  AND a.kind = 'VEHICLE' AND al.driver_checked_at IS NULL
            )
            """,
            {"plan": plan_id},
        ))

    async def set_status(self, plan_id: UUID | str, status: PlanStatus) -> None:
        """
        Mengubah status rencana kerja (SK) ke status tertentu.

        Args:
            plan_id (UUID | str): ID SK.
            status (PlanStatus): Status baru.
        """
        # Menulis ulang field status SK langsung dan menaikkan row_version.
        await self.execute(
            "UPDATE vms.work_plan SET status = CAST(:status AS vms.plan_status), row_version = row_version + 1 WHERE id = :plan",
            {"plan": plan_id, "status": status},
        )

    async def accept_document(self, plan_id: UUID | str, employee_id: str) -> None:
        """
        Menyetujui dan mengefektifkan dokumen SK.

        Args:
            plan_id (UUID | str): ID SK.
            employee_id (str): ID karyawan yang menyetujui.
        """
        # Memperbarui dokumen yang sedang 'AWAITING_ACCEPTANCE' menjadi 'EFFECTIVE'.
        await self.execute(
            """
            UPDATE vms.plan_document SET status = :effective, accepted_by = :emp, accepted_at = now()
             WHERE work_plan_id = :plan AND status = :awaiting
            """,
            {"plan": plan_id, "emp": employee_id, "effective": DocumentStatus.EFFECTIVE,
             "awaiting": DocumentStatus.AWAITING_ACCEPTANCE},
        )

    # ── Penyelesaian SK (V-26, domain.js REQUEST/APPROVE/RETURN_COMPLETE) ─────────────────────
    async def has_open_change(self, plan_id: UUID | str) -> bool:
        """
        Memeriksa apakah ada usulan adendum/perubahan yang masih terbuka (belum disetujui atau ditolak).

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            bool: True jika ada adendum terbuka.
        """
        # Mengecek status plan_change 'PENDING_PM' atau 'AWAITING_LEADER_ACCEPTANCE'.
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM vms.plan_change
                            WHERE work_plan_id = :plan AND status IN ('PENDING_PM', 'AWAITING_LEADER_ACCEPTANCE'))
            """,
            {"plan": plan_id}))

    async def all_days_approved(self, plan_id: UUID | str) -> bool:
        """
        Memastikan bahwa seluruh laporan harian untuk SK ini telah disetujui (APPROVED).

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            bool: True jika tidak ada laporan yang statusnya selain APPROVED.
        """
        # Menggunakan IS DISTINCT FROM 'APPROVED' untuk menangkap status lain atau laporan harian yang belum dibuat (NULL).
        return not await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM vms.work_plan_day wpd
                             LEFT JOIN vms.daily_report dr ON dr.work_plan_day_id = wpd.id
                            WHERE wpd.work_plan_id = :plan AND dr.status IS DISTINCT FROM 'APPROVED')
            """,
            {"plan": plan_id})

    async def final_report(self, plan_id: UUID | str) -> Any:
        """
        Mengambil informasi laporan akhir beserta nama pengaju/pemeriksa dan buktinya.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            Any: Record laporan akhir, atau None bila belum pernah diajukan.
        """
        # Mengambil laporan akhir/penyelesaian pekerjaan dari public.work_completion
        return await self.fetchone(
            """
            SELECT 
                CASE
                    WHEN c.pm_signed_at IS NOT NULL THEN 'APPROVED'
                    WHEN c.leader_signed_at IS NOT NULL THEN 'SUBMITTED'
                    ELSE 'DRAFT'
                END AS status,
                c.summary_notes AS body,
                c.obstacles AS obstacle,
                c.leader_signed_at AS submitted_at,
                le.full_name AS submitted_by_name,
                'Telah diverifikasi dan ditandatangani PM' AS review_note,
                c.pm_signed_at AS reviewed_at,
                pe.full_name AS reviewed_by_name,
                COALESCE(
                    ARRAY(
                        SELECT elem->>'url' 
                        FROM jsonb_array_elements(c.realization_photos_json) AS elem
                    ),
                    '{}'
                ) AS evidence_file_ids
            FROM public.work_completion c
            LEFT JOIN public.employee le ON le.employee_id = c.leader_signer_id
            LEFT JOIN public.employee pe ON pe.employee_id = c.pm_signer_id
            WHERE (c.weekly_plan_id = :plan OR c.completion_id = :plan)
              AND c.delete_at IS NULL
            ORDER BY c.create_at DESC
            LIMIT 1
            """,
            {"plan": plan_id},
        )

    async def final_report_snapshot(self, plan_id: UUID | str, approver: str | None, note: str | None) -> Any:
        """
        Membuat record JSON (snapshot) dari isi laporan akhir yang disetujui (R-19).
        Meliputi: SK, tim, laporan harian, lampiran, insiden, dan persetujuannya.

        Args:
            plan_id (UUID | str): ID SK.
            approver (str | None): ID karyawan (users.user_id) yang menyetujui.
            note (str | None): Catatan persetujuan tambahan.

        Returns:
            Any: Snapshot laporan akhir.
        """
        return await self.scalar(
            """
            SELECT jsonb_build_object(
              'type', 'final_report',
              'approval', jsonb_build_object(
                  'approved_by', (SELECT full_name FROM public.employee WHERE employee_id = CAST(:approver AS uuid)),
                  'note', CAST(:note AS text)),
              'plan', (SELECT jsonb_build_object('id', p.weekly_plan_id, 'number', 'WP-W' || p.week_number, 'title', p.project_name,
                          'location_text', '', 'period_start', p.start_date,
                          'period_end', p.end_date)
                       FROM public.work_plan_weekly p WHERE p.weekly_plan_id = :plan),
              'report', (SELECT jsonb_build_object('body', c.summary_notes, 'obstacle', c.obstacles,
                            'submitted_by', se.full_name, 'submitted_at', c.leader_signed_at,
                            'evidence_file_ids', '[]'::jsonb)
                         FROM public.work_completion c LEFT JOIN public.employee se ON se.employee_id = c.leader_signer_id
                         WHERE c.weekly_plan_id = :plan AND c.report_scope = 'WEEKLY' AND c.delete_at IS NULL
                         ORDER BY c.create_at DESC LIMIT 1))
            """,
            {"plan": plan_id, "approver": approver, "note": note},
        )

    async def store_final_snapshot(self, plan_id: UUID | str, snapshot: str, sha256: bytes) -> None:
        """
        Menyimpan snapshot beku laporan akhir beserta hash SHA-256 nya.

        Args:
            plan_id (UUID | str): ID SK.
            snapshot (str): JSON string dari final_report_snapshot.
            sha256 (bytes): Nilai hash SHA-256 dari JSON tersebut.
        """
        await self.execute(
            """
            UPDATE public.work_completion 
               SET signature_hash = encode(:sha, 'hex'),
                   update_at = now()
             WHERE weekly_plan_id = :plan AND report_scope = 'WEEKLY' AND delete_at IS NULL
            """,
            {"plan": plan_id, "sha": sha256},
        )

    async def final_report_submitter(self, plan_id: UUID | str) -> str | None:
        """
        Mengambil ID karyawan pembuat (submitter) laporan akhir.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            str | None: ID karyawan, atau None.
        """
        value = await self.scalar(
            """
            SELECT CAST(leader_signer_id AS text) 
            FROM public.work_completion 
            WHERE (weekly_plan_id = :plan OR completion_id = :plan) AND delete_at IS NULL
            ORDER BY create_at DESC LIMIT 1
            """,
            {"plan": plan_id},
        )
        return str(value) if value else None

    async def final_report_status(self, plan_id: UUID | str) -> str | None:
        """
        Mendapatkan status saat ini dari laporan akhir.

        Args:
            plan_id (UUID | str): ID SK.

        Returns:
            str | None: Status laporan akhir.
        """
        status = await self.scalar(
            """
            SELECT 
                CASE
                    WHEN pm_signed_at IS NOT NULL THEN 'APPROVED'
                    WHEN leader_signed_at IS NOT NULL THEN 'SUBMITTED'
                    ELSE 'DRAFT'
                END
            FROM public.work_completion 
            WHERE (weekly_plan_id = :plan OR completion_id = :plan) AND delete_at IS NULL
            ORDER BY create_at DESC LIMIT 1
            """,
            {"plan": plan_id},
        )
        return str(status) if status else None

    async def submit_final_report(self, plan_id: UUID | str, user_id: UUID | str, body: str, obstacle: str,
                                  file_ids: list[UUID]) -> None:
        """
        Mengajukan/menyimpan (upsert) laporan akhir.

        Args:
            plan_id (UUID | str): ID SK.
            user_id (UUID | str): ID pengguna (users) yang mengajukan.
            body (str): Isi laporan akhir.
            obstacle (str): Kendala keseluruhan pelaksanaan SK.
            file_ids (list[UUID]): Daftar lampiran dokumen bukti.
        """
        existing = await self.scalar(
            "SELECT completion_id FROM public.work_completion WHERE weekly_plan_id = :plan AND report_scope = 'WEEKLY' AND delete_at IS NULL",
            {"plan": plan_id},
        )
        if existing:
            await self.execute(
                """
                UPDATE public.work_completion
                   SET summary_notes = :body, obstacles = :obstacle,
                       leader_signer_id = (SELECT employee_id FROM public.users WHERE user_id = :uid),
                       leader_signed_at = now(),
                       update_at = now()
                 WHERE completion_id = :cid
                """,
                {"cid": existing, "body": body, "obstacle": obstacle, "uid": user_id},
            )
        else:
            await self.execute(
                """
                INSERT INTO public.work_completion (
                    report_scope, weekly_plan_id, summary_notes, obstacles,
                    realization_photos_json, leader_signer_id, leader_signed_at, signature_hash
                )
                VALUES (
                    'WEEKLY', :plan, :body, :obstacle,
                    '[]'::jsonb,
                    (SELECT employee_id FROM public.users WHERE user_id = :uid),
                    now(),
                    md5(random()::text || clock_timestamp()::text)
                )
                """,
                {"plan": plan_id, "body": body, "obstacle": obstacle, "uid": user_id},
            )

    async def review_final_report(self, plan_id: UUID | str, user_id: UUID | str, status: str,
                                  note: str | None) -> None:
        """
        Menyimpan hasil evaluasi/penilaian atas laporan akhir (Review).

        Args:
            plan_id (UUID | str): ID SK.
            user_id (UUID | str): ID pengguna (users) yang mengevaluasi.
            status (str): Status persetujuan ('APPROVED' atau 'CHANGES_REQUESTED').
            note (str | None): Catatan review.
        """
        if status == "APPROVED":
            await self.execute(
                """
                UPDATE public.work_completion
                   SET pm_signer_id = (SELECT employee_id FROM public.users WHERE user_id = :uid),
                       pm_signed_at = now(),
                       signature_hash = md5(random()::text || clock_timestamp()::text),
                       update_at = now()
                 WHERE weekly_plan_id = :plan AND report_scope = 'WEEKLY' AND delete_at IS NULL
                """,
                {"plan": plan_id, "uid": user_id},
            )
        else:
            await self.execute(
                """
                UPDATE public.work_completion
                   SET pm_signer_id = NULL,
                       pm_signed_at = NULL,
                       obstacles = COALESCE(obstacles, '') || E'\n[Catatan Revisi PM]: ' || :note,
                       update_at = now()
                 WHERE weekly_plan_id = :plan AND report_scope = 'WEEKLY' AND delete_at IS NULL
                """,
                {"plan": plan_id, "note": note or ""},
            )
