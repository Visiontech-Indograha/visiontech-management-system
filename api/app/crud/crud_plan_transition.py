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
        Memulai SK yang sudah Diterima dan tanggal mulainya sudah tiba hari ini (menjadi IN_PROGRESS).
        
        Args:
            org_id (UUID | str): ID organisasi.
            today (Any): Tanggal batas mulai (hari ini).
            
        Returns:
            list[str]: Daftar ID rencana kerja yang baru saja diaktifkan/dimulai.
        """
        # Melakukan UPDATE dan langsung mengembalikan ID record yang berhasil diubah dengan RETURNING.
        rows = await self.fetchall(
            """
            UPDATE vms.work_plan
               SET status = CAST(:running AS vms.plan_status), row_version = row_version + 1
             WHERE organization_id = CAST(:org AS uuid) AND status = 'ACCEPTED' AND deleted_at IS NULL
               AND lower(period) <= :today
            RETURNING CAST(id AS text) AS id
            """,
            {"org": str(org_id), "today": today, "running": PlanStatus.IN_PROGRESS},
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
        # Menghitung selisih (jumlah hari SK) lalu membandingkannya dengan
        # jumlah baris vms.work_plan_day yang memenuhi syarat judul terisi
        # serta memiliki setidaknya satu tugas tanpa judul kosong.
        return bool(await self.scalar(
            """
            SELECT
              (SELECT count(*) FROM vms.work_plan_day d
                 WHERE d.work_plan_id = wp.id AND d.work_date <@ wp.period
                   AND btrim(d.title) <> ''
                   AND EXISTS (SELECT 1 FROM vms.work_plan_task t WHERE t.work_plan_day_id = d.id)
                   AND NOT EXISTS (SELECT 1 FROM vms.work_plan_task t
                                   WHERE t.work_plan_day_id = d.id AND btrim(t.title) = ''))
              = (upper(wp.period) - lower(wp.period))
            FROM vms.work_plan wp WHERE wp.id = :plan
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
                   pm.full_name AS pm_name, pm.position AS pm_position
                  FROM vms.work_plan wp
                  LEFT JOIN vms.business_unit bu ON bu.id = wp.unit_id
                  LEFT JOIN vms.site s ON s.id = wp.site_id
                  LEFT JOIN vms.employee pm ON pm.id = wp.pm_employee_id
                  WHERE wp.id = :plan) p),
              'team', COALESCE((SELECT jsonb_agg(jsonb_build_object('employee_id', m.employee_id,
                                        'full_name', e.full_name, 'position', e.position,
                                        'role_in_plan', m.role_in_plan)
                                        ORDER BY m.role_in_plan, e.full_name)
                                FROM vms.work_plan_member m JOIN vms.employee e ON e.id = m.employee_id
                                WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)), '[]'),
              'days', COALESCE((SELECT jsonb_agg(jsonb_build_object('work_date', d.work_date, 'title', d.title,
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
        value = await self.scalar("SELECT employee_id::text FROM vms.app_user WHERE id = :uid", {"uid": user_id})
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
        # Mengeksekusi function internal vms.is_plan_leader untuk cek otoritas leader.
        return bool(await self.scalar("SELECT vms.is_plan_leader(:plan, :user)", {"plan": plan_id, "user": user_id}))

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
                   number = COALESCE(number, 'SK-' || to_char(CURRENT_DATE, 'YYYYMM') || '-' || right(id::text, 8))
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
        Mengaktifkan status aset (alat/kendaraan) yang dipesan untuk SK agar berstatus 'IN_USE'.
        
        Args:
            plan_id (UUID | str): ID SK.
        """
        # Alat (TOOL) langsung aktif menjadi 'IN_USE'.
        # Sedangkan kendaraan (VEHICLE) mensyaratkan driver_checked_at sudah tidak NULL 
        # (kendaraan telah diperiksa fisiknya oleh pengemudi yang ditunjuk).
        await self.execute(
            """
            UPDATE vms.asset a SET status = 'IN_USE', updated_at = now()
              FROM vms.asset_allocation al
             WHERE al.asset_id = a.id AND al.work_plan_id = :plan AND al.released_at IS NULL
               AND a.status = 'RESERVED' AND (a.kind = 'TOOL' OR al.driver_checked_at IS NOT NULL)
            """,
            {"plan": plan_id},
        )

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
        # Menggabungkan final_report dengan array data ID file dari final_report_evidence.
        return await self.fetchone(
            """
            SELECT CAST(fr.status AS text) AS status, fr.body, fr.obstacle,
                   fr.submitted_at, se.full_name AS submitted_by_name,
                   fr.review_note, fr.reviewed_at, re.full_name AS reviewed_by_name,
                   COALESCE(ARRAY(SELECT CAST(ev.file_id AS text) FROM vms.final_report_evidence ev
                                  WHERE ev.work_plan_id = fr.work_plan_id ORDER BY ev.file_id), '{}')
                       AS evidence_file_ids
            FROM vms.final_report fr
            LEFT JOIN vms.employee se ON se.id = fr.submitted_by
            LEFT JOIN vms.employee re ON re.id = fr.reviewed_by
            WHERE fr.work_plan_id = :plan
            """,
            {"plan": plan_id})

    async def final_report_snapshot(self, plan_id: UUID | str, approver: str | None, note: str | None) -> Any:
        """
        Membuat record JSON (snapshot) dari isi laporan akhir yang disetujui (R-19).
        Meliputi: SK, tim, laporan harian, lampiran, insiden, dan persetujuannya.
        
        Args:
            plan_id (UUID | str): ID SK.
            approver (str | None): ID karyawan (app_user.id) yang menyetujui.
            note (str | None): Catatan persetujuan tambahan.
            
        Returns:
            Any: Snapshot laporan akhir.
        """
        # Pembangunan JSONB komprehensif agar riwayat penyelesaian tercetak
        # dengan kondisi data real-time pada saat laporan akhir ini disetujui.
        return await self.scalar(
            """
            SELECT jsonb_build_object(
              'type', 'final_report',
              'approval', jsonb_build_object(
                  'approved_by', (SELECT full_name FROM vms.employee WHERE id = CAST(:approver AS uuid)),
                  'note', CAST(:note AS text)),
              'plan', (SELECT jsonb_build_object('id', p.id, 'number', p.number, 'title', p.title,
                          'location_text', p.location_text, 'period_start', lower(p.period),
                          'period_end', upper(p.period) - 1)
                       FROM vms.work_plan p WHERE p.id = :plan),
              'team', COALESCE((SELECT jsonb_agg(jsonb_build_object('full_name', e.full_name,
                                          'role_in_plan', m.role_in_plan) ORDER BY m.role_in_plan, e.full_name)
                                FROM vms.work_plan_member m JOIN vms.employee e ON e.id = m.employee_id
                                WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)), '[]'::jsonb),
              'report', (SELECT jsonb_build_object('body', fr.body, 'obstacle', fr.obstacle,
                            'submitted_by', se.full_name, 'submitted_at', fr.submitted_at,
                            'evidence_file_ids', COALESCE((SELECT jsonb_agg(ev.file_id ORDER BY ev.file_id)
                                FROM vms.final_report_evidence ev WHERE ev.work_plan_id = fr.work_plan_id),
                                '[]'::jsonb))
                         FROM vms.final_report fr LEFT JOIN vms.employee se ON se.id = fr.submitted_by
                         WHERE fr.work_plan_id = :plan),
              'incidents', COALESCE((SELECT jsonb_agg(jsonb_build_object('category', i.category,
                                'severity', i.severity, 'description', i.description, 'occurred_on', i.occurred_on,
                                'status', i.status) ORDER BY i.occurred_on, i.created_at)
                                FROM vms.incident_report i WHERE i.work_plan_id = :plan), '[]'::jsonb))
            """,
            {"plan": plan_id, "approver": approver, "note": note})

    async def store_final_snapshot(self, plan_id: UUID | str, snapshot: str, sha256: bytes) -> None:
        """
        Menyimpan snapshot beku laporan akhir beserta hash SHA-256 nya.
        
        Args:
            plan_id (UUID | str): ID SK.
            snapshot (str): JSON string dari final_report_snapshot.
            sha256 (bytes): Nilai hash SHA-256 dari JSON tersebut.
        """
        # Mengisi snapshot dan snapshot_sha256 pada tabel final_report.
        await self.execute(
            "UPDATE vms.final_report SET snapshot = CAST(:snap AS jsonb), snapshot_sha256 = :sha "
            "WHERE work_plan_id = :plan",
            {"plan": plan_id, "snap": snapshot, "sha": sha256})

    async def final_report_submitter(self, plan_id: UUID | str) -> str | None:
        """
        Mengambil ID karyawan pembuat (submitter) laporan akhir.
        
        Args:
            plan_id (UUID | str): ID SK.
            
        Returns:
            str | None: ID karyawan, atau None.
        """
        value = await self.scalar(
            "SELECT CAST(submitted_by AS text) FROM vms.final_report WHERE work_plan_id = :plan", {"plan": plan_id})
        return str(value) if value else None

    async def final_report_status(self, plan_id: UUID | str) -> str | None:
        """
        Mendapatkan status saat ini dari laporan akhir.
        
        Args:
            plan_id (UUID | str): ID SK.
            
        Returns:
            str | None: Status laporan akhir.
        """
        status: str | None = await self.scalar(
            "SELECT CAST(status AS text) FROM vms.final_report WHERE work_plan_id = :plan", {"plan": plan_id})
        return status

    async def submit_final_report(self, plan_id: UUID | str, user_id: UUID | str, body: str, obstacle: str,
                                  file_ids: list[UUID]) -> None:
        """
        Mengajukan/menyimpan (upsert) laporan akhir.
        
        Args:
            plan_id (UUID | str): ID SK.
            user_id (UUID | str): ID pengguna (app_user) yang mengajukan.
            body (str): Isi laporan akhir.
            obstacle (str): Kendala keseluruhan pelaksanaan SK.
            file_ids (list[UUID]): Daftar lampiran dokumen bukti.
        """
        # Melakukan UPSERT: Jika sudah pernah diajukan, status kembali ke 'SUBMITTED' dan body terbarui.
        await self.execute(
            """
            INSERT INTO vms.final_report (work_plan_id, status, body, obstacle, submitted_by, submitted_at)
            VALUES (:plan, 'SUBMITTED', :body, :obstacle,
                    (SELECT employee_id FROM vms.app_user WHERE id = :uid), now())
            ON CONFLICT (work_plan_id) DO UPDATE
               SET status = 'SUBMITTED', body = EXCLUDED.body, obstacle = EXCLUDED.obstacle,
                   submitted_by = EXCLUDED.submitted_by, submitted_at = now()
            """,
            {"plan": plan_id, "uid": user_id, "body": body, "obstacle": obstacle},
        )
        # Menghapus dan menulis ulang relasi file untuk tabel final_report_evidence.
        await self.execute("DELETE FROM vms.final_report_evidence WHERE work_plan_id = :plan", {"plan": plan_id})
        if file_ids:
            await self.execute(
                """
                INSERT INTO vms.final_report_evidence (work_plan_id, file_id)
                SELECT :plan, unnest(CAST(:fids AS uuid[]))
                """,
                {"plan": plan_id, "fids": [str(f) for f in file_ids]})

    async def review_final_report(self, plan_id: UUID | str, user_id: UUID | str, status: str,
                                  note: str | None) -> None:
        """
        Menyimpan hasil evaluasi/penilaian atas laporan akhir (Review).
        
        Args:
            plan_id (UUID | str): ID SK.
            user_id (UUID | str): ID pengguna (app_user) yang mengevaluasi.
            status (str): Status persetujuan ('APPROVED' atau 'CHANGES_REQUESTED').
            note (str | None): Catatan review.
        """
        # Mengubah status final_report, merekam catatan, dan timestamp reviewed_at.
        await self.execute(
            """
            UPDATE vms.final_report
               SET status = CAST(:status AS vms.report_status), review_note = :note, reviewed_at = now(),
                   reviewed_by = (SELECT employee_id FROM vms.app_user WHERE id = :uid)
             WHERE work_plan_id = :plan
            """,
            {"plan": plan_id, "uid": user_id, "status": status, "note": note},
        )
