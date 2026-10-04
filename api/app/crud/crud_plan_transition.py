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

    async def lock_plan(self, plan_id: UUID | str, org_id: UUID | str, include_archived: bool = False) -> Any:
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
        """domain.js CANCEL_PLAN: SK batal; usulan terbuka & dokumen ditarik; aset yang masih dipesan dilepas.
        Skema tidak punya status CANCELLED untuk dokumen/usulan → WITHDRAWN (dok 10 Bagian C)."""
        await self.execute(
            """
            UPDATE vms.work_plan
               SET status = CAST(:cancelled AS vms.plan_status), cancellation_reason = :reason,
                   row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "reason": reason, "cancelled": PlanStatus.CANCELLED},
        )
        await self.execute(
            """
            UPDATE vms.plan_change SET status = CAST(:withdrawn AS vms.change_status)
             WHERE work_plan_id = :plan AND status IN ('PENDING_PM', 'AWAITING_LEADER_ACCEPTANCE')
            """,
            {"plan": plan_id, "withdrawn": ChangeStatus.WITHDRAWN},
        )
        await self.execute(
            "UPDATE vms.plan_document SET status = CAST(:withdrawn AS vms.document_status) WHERE work_plan_id = :plan",
            {"plan": plan_id, "withdrawn": DocumentStatus.WITHDRAWN},
        )
        # Aset yang baru dipesan dilepas; yang sedang dipakai tetap wajib dikembalikan (prototipe).
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
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.plan_document WHERE work_plan_id = :plan)", {"plan": plan_id}))

    async def has_active_allocation(self, plan_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.asset_allocation WHERE work_plan_id = :plan AND released_at IS NULL)",
            {"plan": plan_id}))

    async def archive(self, plan_id: UUID | str, user_id: UUID | str, reason: str) -> None:
        """domain.js DELETE_PLAN: soft delete — riwayat tetap ada."""
        await self.execute(
            """
            UPDATE vms.work_plan
               SET deleted_at = now(), deleted_by = :user, deletion_reason = :reason, row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "user": user_id, "reason": reason},
        )

    async def restore(self, plan_id: UUID | str) -> None:
        """domain.js RESTORE_PLAN — alasan pengarsipan tetap disimpan sebagai riwayat."""
        await self.execute(
            "UPDATE vms.work_plan SET deleted_at = NULL, deleted_by = NULL, row_version = row_version + 1 WHERE id = :plan",
            {"plan": plan_id},
        )

    async def get_plan(self, plan_id: UUID | str) -> Any:
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
        """domain.js APPEAL (alur v2: Ajukan adendum): SK terbit → APPEALED dengan alasan."""
        await self.execute(
            """
            UPDATE vms.work_plan
               SET status = CAST(:appealed AS vms.plan_status), appeal_reason = :reason, row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "reason": reason, "appealed": PlanStatus.APPEALED},
        )
        # Alur SK v2: dokumen yang menunggu tanda tangan ketua tidak berlaku lagi (direvisi PM).
        await self.execute(
            "UPDATE vms.plan_document SET status = CAST(:superseded AS vms.document_status) "
            "WHERE work_plan_id = :plan AND status = :awaiting",
            {"plan": plan_id, "superseded": DocumentStatus.SUPERSEDED, "awaiting": DocumentStatus.AWAITING_ACCEPTANCE},
        )

    async def start_due(self, org_id: UUID | str, today: Any) -> list[str]:
        """SK Diterima yang tanggal mulainya sudah tiba → Berjalan. Mengembalikan id yang berubah."""
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
        """domain.js REVISE: kembali ke DRAFT, revisi berikutnya; semua dokumen lama digantikan."""
        await self.execute(
            """
            UPDATE vms.work_plan
               SET status = CAST(:draft AS vms.plan_status), revision = revision + 1, row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "draft": PlanStatus.DRAFT},
        )
        await self.execute(
            "UPDATE vms.plan_document SET status = CAST(:superseded AS vms.document_status) WHERE work_plan_id = :plan",
            {"plan": plan_id, "superseded": DocumentStatus.SUPERSEDED},
        )

    async def active_team(self, plan_id: UUID | str) -> list[Any]:
        """Anggota aktif (valid_period terbuka) beserta status karyawannya."""
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
        """Setiap tanggal periode punya hari berjudul dengan ≥ 1 tugas berjudul (domain.js PUBLISH)."""
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
        """Isi beku dokumen: SK, tim aktif, hari beserta tugasnya, lampiran (domain.js snapshot)."""
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
        value = await self.scalar("SELECT employee_id::text FROM vms.app_user WHERE id = :uid", {"uid": user_id})
        return str(value) if value else None

    async def is_leader(self, plan_id: UUID | str, user_id: UUID | str) -> bool:
        return bool(await self.scalar("SELECT vms.is_plan_leader(:plan, :user)", {"plan": plan_id, "user": user_id}))

    async def publish(self, plan_id: UUID | str) -> None:
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
        await self.execute(
            """
            INSERT INTO vms.plan_document (work_plan_id, kind, version, number, status, snapshot, snapshot_sha256, issued_by)
            SELECT id, CAST(:kind AS vms.document_kind), :version, number, CAST(:status AS vms.document_status),
                   CAST(:snapshot AS jsonb), ''::bytea, :issued_by   -- hash dihitung trigger plan_document_hash
            FROM vms.work_plan WHERE id = :plan
            """,
            {
                "plan": plan_id, "version": revision, "snapshot": snapshot, "issued_by": issued_by,
                "kind": DocumentKind.INITIAL_ORDER if revision == 1 else DocumentKind.REVISION,
                "status": DocumentStatus.AWAITING_ACCEPTANCE,
            },
        )

    async def activate_reserved_assets(self, plan_id: UUID | str) -> None:
        """domain.js START: reservasi SK menjadi IN_USE — alat langsung, kendaraan setelah diperiksa pengemudi."""
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
        await self.execute(
            "UPDATE vms.work_plan SET status = CAST(:status AS vms.plan_status), row_version = row_version + 1 WHERE id = :plan",
            {"plan": plan_id, "status": status},
        )

    async def accept_document(self, plan_id: UUID | str, employee_id: str) -> None:
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
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM vms.plan_change
                            WHERE work_plan_id = :plan AND status IN ('PENDING_PM', 'AWAITING_LEADER_ACCEPTANCE'))
            """,
            {"plan": plan_id}))

    async def all_days_approved(self, plan_id: UUID | str) -> bool:
        return not await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM vms.work_plan_day wpd
                             LEFT JOIN vms.daily_report dr ON dr.work_plan_day_id = wpd.id
                            WHERE wpd.work_plan_id = :plan AND dr.status IS DISTINCT FROM 'APPROVED')
            """,
            {"plan": plan_id})

    async def final_report(self, plan_id: UUID | str) -> Any:
        """Laporan akhir beserta nama pengaju/pemeriksa dan bukti. None bila belum pernah diajukan."""
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
        """Isi laporan akhir yang dibekukan saat disetujui (R-19): SK, tim, laporan, lampiran, insiden,
        dan persetujuannya."""
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
        await self.execute(
            "UPDATE vms.final_report SET snapshot = CAST(:snap AS jsonb), snapshot_sha256 = :sha "
            "WHERE work_plan_id = :plan",
            {"plan": plan_id, "snap": snapshot, "sha": sha256})

    async def final_report_submitter(self, plan_id: UUID | str) -> str | None:
        value = await self.scalar(
            "SELECT CAST(submitted_by AS text) FROM vms.final_report WHERE work_plan_id = :plan", {"plan": plan_id})
        return str(value) if value else None

    async def final_report_status(self, plan_id: UUID | str) -> str | None:
        status: str | None = await self.scalar(
            "SELECT CAST(status AS text) FROM vms.final_report WHERE work_plan_id = :plan", {"plan": plan_id})
        return status

    async def submit_final_report(self, plan_id: UUID | str, user_id: UUID | str, body: str, obstacle: str,
                                  file_ids: list[UUID]) -> None:
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
        await self.execute(
            """
            UPDATE vms.final_report
               SET status = CAST(:status AS vms.report_status), review_note = :note, reviewed_at = now(),
                   reviewed_by = (SELECT employee_id FROM vms.app_user WHERE id = :uid)
             WHERE work_plan_id = :plan
            """,
            {"plan": plan_id, "uid": user_id, "status": status, "note": note},
        )
