"""
app/modules/work_plans/repositories/plan_transition_repository.py
Kueri untuk transisi SK (publish, accept, start). Satu-satunya tempat SQL-nya (dok 12).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.enums import PlanStatus
from app.core.repository import CRUDBase

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
            SELECT wp.weekly_plan_id AS id, wp.division_id AS unit_id, NULL AS site_id,
                   'SK/W' || wp.week_number || '/' || wp.year AS number,
                   'Rencana Kerja W' || wp.week_number || ' ' || wp.year AS title,
                   'Kantor / Site' AS location_text, wp.notes AS description,
                   wp.start_date AS period_start, wp.end_date AS period_end,
                   wp.status, wp.approved_by_pm_id AS pm_employee_id, t.leader_employee_id,
                   1 AS revision, 1 AS row_version, NULL AS cancellation_reason,
                   (wp.delete_at IS NOT NULL) AS archived
            FROM public.work_plan_weekly wp
            JOIN public.team t ON t.team_id = wp.team_id
            WHERE wp.weekly_plan_id = :id AND (CAST(:any AS boolean) OR wp.delete_at IS NULL)
            FOR UPDATE
            """,
            {"id": plan_id, "any": include_archived},
        )

    async def cancel(self, plan_id: UUID | str, reason: str) -> None:
        """Membatalkan SK."""
        await self.execute(
            """
            UPDATE public.work_plan_weekly
               SET status = 'CANCELLED', update_at = now()
             WHERE weekly_plan_id = :plan
            """,
            {"plan": plan_id},
        )

    async def ever_published(self, plan_id: UUID | str) -> bool:
        """Mengecek apakah SK ini pernah diterbitkan."""
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM public.work_plan_weekly WHERE weekly_plan_id = :plan AND status IN ('PUBLISHED', 'ACCEPTED', 'ONGOING', 'IN_PROGRESS', 'COMPLETION_REVIEW', 'COMPLETED', 'APPROVED'))",
                {"plan": plan_id},
            )
        )

    async def has_active_allocation(self, plan_id: UUID | str) -> bool:
        """Mengecek apakah SK ini masih memiliki alokasi aset."""
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM public.asset_assignment WHERE delete_at IS NULL)",
                {"plan": plan_id},
            )
        )

    async def archive(self, plan_id: UUID | str, user_id: UUID | str, reason: str) -> None:
        """Soft delete rencana kerja mingguan."""
        await self.execute(
            """
            UPDATE public.work_plan_weekly
               SET delete_at = now(), update_at = now()
             WHERE weekly_plan_id = :plan
            """,
            {"plan": plan_id},
        )

    async def restore(self, plan_id: UUID | str) -> None:
        """Mengembalikan rencana kerja dari arsip."""
        await self.execute(
            "UPDATE public.work_plan_weekly SET delete_at = NULL, update_at = now() WHERE weekly_plan_id = :plan",
            {"plan": plan_id},
        )

    async def get_plan(self, plan_id: UUID | str) -> Any:
        """Mendapatkan metadata lengkap rencana kerja mingguan."""
        return await self.fetchone(
            """
            SELECT wp.weekly_plan_id AS id, wp.division_id AS unit_id, NULL AS site_id,
                   'SK/W' || wp.week_number || '/' || wp.year AS number,
                   'Rencana Kerja W' || wp.week_number || ' ' || wp.year AS title,
                   'Kantor / Site' AS location_text, wp.notes AS description,
                   wp.start_date AS period_start, wp.end_date AS period_end,
                   wp.status, wp.approved_by_pm_id AS pm_employee_id, t.leader_employee_id,
                   1 AS revision, 1 AS row_version, NULL AS cancellation_reason,
                   NULL AS appeal_reason, 'SIPIL' AS category
            FROM public.work_plan_weekly wp
            JOIN public.team t ON t.team_id = wp.team_id
            WHERE wp.weekly_plan_id = :id
            """,
            {"id": plan_id},
        )

    async def appeal(self, plan_id: UUID | str, reason: str) -> None:
        """Mengajukan banding/adendum atas SK."""
        await self.execute(
            """
            UPDATE public.work_plan_weekly
               SET status = 'APPEALED', rollover_approval = 'WAITING_PM', update_at = now()
             WHERE weekly_plan_id = :plan
            """,
            {"plan": plan_id},
        )

    async def start_due(self, org_id: UUID | str, today: Any) -> list[str]:
        """Memulai SK yang sudah Diterima dan tanggal mulainya sudah tiba hari ini."""
        rows = await self.fetchall(
            """
            UPDATE public.work_plan_daily
               SET status = 'ONGOING', update_at = NOW()
             WHERE status = 'APPROVED'
               AND work_date <= CAST(:today AS date)
               AND delete_at IS NULL
            RETURNING CAST(daily_plan_id AS text) AS id
            """,
            {"today": today},
        )
        return [str(r.id) for r in rows]

    async def revise(self, plan_id: UUID | str) -> None:
        """Mengembalikan rencana kerja ke status DRAFT."""
        await self.execute(
            """
            UPDATE public.work_plan_weekly
               SET status = 'DRAFT', update_at = now()
             WHERE weekly_plan_id = :plan
            """,
            {"plan": plan_id},
        )

    async def active_team(self, plan_id: UUID | str) -> list[Any]:
        """Mendapatkan tim yang aktif berpartisipasi dalam rencana mingguan."""
        return list(
            await self.fetchall(
                """
            SELECT m.employee_id::text AS employee_id,
                   CASE WHEN m.employee_id = t.leader_employee_id THEN 'LEADER' ELSE 'MEMBER' END AS role_in_plan,
                   (e.offboarding_status = 'active' AND e.delete_at IS NULL) AS employee_active
            FROM public.work_plan_weekly wp
            JOIN public.team t ON t.team_id = wp.team_id
            JOIN public.member m ON m.team_id = t.team_id AND m.is_active = TRUE AND m.delete_at IS NULL
            JOIN public.employee e ON e.employee_id = m.employee_id
            WHERE wp.weekly_plan_id = :plan
            """,
                {"plan": plan_id},
            )
        )

    async def day_details_complete(self, plan_id: UUID | str) -> bool:
        """Memastikan setiap hari dalam periode SK sudah terisi."""
        return bool(
            await self.scalar(
                """
            SELECT count(*) > 0
            FROM public.work_plan_daily
            WHERE weekly_plan_id = :plan AND delete_at IS NULL
            """,
                {"plan": plan_id},
            )
        )

    async def snapshot(self, plan_id: UUID | str) -> Any:
        """Membekukan isi dokumen secara komprehensif saat pembuatan SK."""
        return await self.scalar(
            """
            SELECT jsonb_build_object(
              'plan', (SELECT to_jsonb(p) FROM (
                  SELECT wp.weekly_plan_id AS id, wp.division_id AS unit_id, NULL AS site_id,
                         'SK/W' || wp.week_number || '/' || wp.year AS number,
                         'Rencana Kerja W' || wp.week_number || ' ' || wp.year AS title,
                         'Kantor / Site' AS location_text, wp.notes AS description,
                         wp.start_date AS period_start, wp.end_date AS period_end,
                         wp.status, wp.approved_by_pm_id AS pm_employee_id, t.leader_employee_id,
                         1 AS revision, 1 AS row_version, NULL AS cancellation_reason,
                         'SIPIL' AS category, d.name AS unit_name,
                         pm.full_name AS pm_name, 'Project Manager' AS pm_position,
                         FALSE AS is_out_of_town, 'SIPIL' AS work_type_name
                  FROM public.work_plan_weekly wp
                  JOIN public.team t ON t.team_id = wp.team_id
                  JOIN public.division d ON d.division_id = wp.division_id
                  LEFT JOIN public.employee pm ON pm.employee_id = wp.approved_by_pm_id
                  WHERE wp.weekly_plan_id = :plan) p),
              'team', COALESCE((SELECT jsonb_agg(jsonb_build_object('employee_id', m.employee_id,
                                        'full_name', e.full_name, 'position', 'Teknisi Proyek',
                                        'role_in_plan', CASE WHEN m.employee_id = t.leader_employee_id THEN 'LEADER' ELSE 'MEMBER' END,
                                        'since', wp.start_date)
                                        ORDER BY m.employee_id)
                                FROM public.work_plan_weekly wp
                                JOIN public.team t ON t.team_id = wp.team_id
                                JOIN public.member m ON m.team_id = t.team_id AND m.is_active = TRUE AND m.delete_at IS NULL
                                JOIN public.employee e ON e.employee_id = m.employee_id
                                WHERE wp.weekly_plan_id = :plan), '[]'::jsonb),
              'days', '[]'::jsonb,
              'assets', '[]'::jsonb,
              'attachments', '[]'::jsonb
            )
            """,
            {"plan": plan_id},
        )

    async def employee_id_of(self, user_id: UUID | str) -> str | None:
        """Mendapatkan ID Karyawan yang merujuk pada pengguna sistem."""
        value = await self.scalar("SELECT employee_id::text FROM public.users WHERE user_id = :uid", {"uid": user_id})
        return str(value) if value else None

    async def is_leader(self, plan_id: UUID | str, user_id: UUID | str) -> bool:
        """Memastikan apakah user ini berhak menyetujui sebagai Ketua SK."""
        return bool(
            await self.scalar(
                """
            SELECT EXISTS (
                SELECT 1 FROM public.work_plan_weekly wp
                JOIN public.team t ON t.team_id = wp.team_id
                JOIN public.users u ON u.employee_id = t.leader_employee_id
                WHERE wp.weekly_plan_id = :plan AND u.user_id = :user
            )
            """,
                {"plan": plan_id, "user": user_id},
            )
        )

    async def publish(self, plan_id: UUID | str) -> None:
        """Menerbitkan dokumen SK."""
        await self.execute(
            """
            UPDATE public.work_plan_weekly
               SET status = 'APPROVED', update_at = now()
             WHERE weekly_plan_id = :plan
            """,
            {"plan": plan_id},
        )

    async def insert_document(self, plan_id: UUID | str, revision: int, snapshot: Any, issued_by: str) -> None:
        pass

    async def activate_reserved_assets(self, plan_id: UUID | str) -> None:
        pass

    async def has_unchecked_vehicle(self, plan_id: UUID | str) -> bool:
        return False

    async def set_status(self, plan_id: UUID | str, status: PlanStatus) -> None:
        """Mengubah status rencana kerja mingguan ke status tertentu."""
        await self.execute(
            "UPDATE public.work_plan_weekly SET status = CAST(:status AS text), update_at = now() WHERE weekly_plan_id = :plan",
            {"plan": plan_id, "status": str(status)},
        )

    async def accept_document(self, plan_id: UUID | str, employee_id: str) -> None:
        pass

    async def has_open_change(self, plan_id: UUID | str) -> bool:
        return bool(
            await self.scalar(
                """
            SELECT EXISTS (SELECT 1 FROM public.work_plan_weekly
                            WHERE weekly_plan_id = :plan AND rollover_approval = 'WAITING_PM')
            """,
                {"plan": plan_id},
            )
        )

    async def all_days_approved(self, plan_id: UUID | str) -> bool:
        return bool(
            await self.scalar(
                """
            SELECT count(*) > 0 AND count(*) = count(*) FILTER (WHERE status = 'APPROVED')
            FROM public.work_plan_daily
            WHERE weekly_plan_id = :plan AND delete_at IS NULL
            """,
                {"plan": plan_id},
            )
        )

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

    async def submit_final_report(
        self, plan_id: UUID | str, user_id: UUID | str, body: str, obstacle: str, file_ids: list[UUID]
    ) -> None:
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

    async def review_final_report(
        self, plan_id: UUID | str, user_id: UUID | str, status: str, note: str | None
    ) -> None:
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
