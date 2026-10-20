"""
app/modules/work_plans/repositories/member_report_repository.py
Laporan harian dan dokumen penyelesaian pekerjaan untuk Master Schema V2.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase


class CRUDMemberReport(CRUDBase):
    """
    Kelas operasi CRUD untuk menangani Laporan Harian Anggota dan Berita Acara Penyelesaian.
    """

    async def employee_of(self, user_id: UUID | str) -> str | None:
        """
        Mendapatkan ID karyawan berdasarkan ID pengguna (users).
        """
        value = await self.scalar(
            "SELECT CAST(employee_id AS text) FROM public.users WHERE user_id = :uid", {"uid": user_id}
        )
        return str(value) if value else None

    async def on_duty(self, day_id: UUID | str, employee_id: UUID | str) -> bool:
        """Karyawan bertugas pada hari itu (anggota tim aktif)."""
        return bool(
            await self.scalar(
                """
            SELECT EXISTS (
                SELECT 1 FROM public.work_plan_daily d
                JOIN public.work_plan_weekly w ON w.weekly_plan_id = d.weekly_plan_id
                JOIN public.member m ON m.team_id = w.team_id
                WHERE d.daily_plan_id = CAST(:day AS uuid)
                  AND m.employee_id = CAST(:emp AS uuid)
                  AND m.is_active = TRUE
                  AND m.delete_at IS NULL
            )
            """,
                {"day": str(day_id), "emp": str(employee_id)},
            )
        )

    async def list_for_day(self, day_id: UUID | str) -> list[Any]:
        """
        Mengambil semua laporan harian untuk hari kerja tertentu.
        """
        return list(
            await self.fetchall(
                """
            SELECT
                c.completion_id AS id,
                CAST(c.leader_signer_id AS text) AS employee_id,
                e.full_name,
                'Team Leader' AS position,
                CASE
                    WHEN c.pm_signed_at IS NOT NULL THEN 'APPROVED'
                    WHEN c.leader_signed_at IS NOT NULL THEN 'SENT'
                    ELSE 'DRAFT'
                END AS status,
                c.summary_notes AS body,
                c.obstacles AS obstacle,
                c.leader_signed_at AS sent_at,
                '{}'::text[] AS evidence_file_ids,
                COALESCE(c.realization_photos_json, '[]'::jsonb) AS evidence
            FROM public.work_completion c
            LEFT JOIN public.employee e ON e.employee_id = c.leader_signer_id
            WHERE c.daily_plan_id = :day AND c.report_scope = 'DAILY' AND c.delete_at IS NULL
            ORDER BY c.create_at DESC
            """,
                {"day": day_id},
            )
        )

    async def mine(self, day_id: UUID | str, employee_id: str) -> Any:
        """
        Mengambil satu laporan harian milik karyawan spesifik pada hari tertentu.
        """
        return await self.fetchone(
            """
            SELECT
                c.completion_id AS id,
                CAST(c.leader_signer_id AS text) AS employee_id,
                e.full_name,
                'Team Leader' AS position,
                CASE
                    WHEN c.pm_signed_at IS NOT NULL THEN 'APPROVED'
                    WHEN c.leader_signed_at IS NOT NULL THEN 'SENT'
                    ELSE 'DRAFT'
                END AS status,
                c.summary_notes AS body,
                c.obstacles AS obstacle,
                c.leader_signed_at AS sent_at,
                '{}'::text[] AS evidence_file_ids,
                COALESCE(c.realization_photos_json, '[]'::jsonb) AS evidence
            FROM public.work_completion c
            LEFT JOIN public.employee e ON e.employee_id = c.leader_signer_id
            WHERE c.daily_plan_id = :day
              AND c.leader_signer_id = CAST(:emp AS uuid)
              AND c.report_scope = 'DAILY'
              AND c.delete_at IS NULL
            ORDER BY c.create_at DESC LIMIT 1
            """,
            {"day": day_id, "emp": employee_id},
        )

    async def save(self, day_id: UUID | str, employee_id: str, body: str, obstacle: str) -> Any:
        """
        Menyimpan draf laporan harian.
        """
        existing = await self.scalar(
            """
            SELECT completion_id FROM public.work_completion
            WHERE daily_plan_id = :day AND leader_signer_id = CAST(:emp AS uuid)
              AND report_scope = 'DAILY' AND delete_at IS NULL
            """,
            {"day": day_id, "emp": employee_id},
        )
        if existing:
            return await self.fetchone(
                """
                UPDATE public.work_completion
                   SET summary_notes = :body, obstacles = :obstacle, update_at = now()
                 WHERE completion_id = :cid
                RETURNING completion_id AS id
                """,
                {"cid": existing, "body": body, "obstacle": obstacle},
            )
        else:
            return await self.fetchone(
                """
                INSERT INTO public.work_completion (
                    report_scope, daily_plan_id, weekly_plan_id, summary_notes, obstacles,
                    realization_photos_json, leader_signer_id, signature_hash
                )
                VALUES (
                    'DAILY', :day,
                    (SELECT weekly_plan_id FROM public.work_plan_daily WHERE daily_plan_id = :day),
                    :body, :obstacle, '[]'::jsonb, CAST(:emp AS uuid),
                    md5(random()::text || clock_timestamp()::text)
                )
                RETURNING completion_id AS id
                """,
                {"day": day_id, "emp": employee_id, "body": body, "obstacle": obstacle},
            )

    async def replace_evidence(self, report_id: UUID | str, items: list[tuple[str, str | None, str]]) -> None:
        """
        Mengganti seluruh lampiran bukti foto penyelesaian.
        """
        photos = [{"url": f, "slot_label": s, "source": src} for f, s, src in items]
        await self.execute(
            """
            UPDATE public.work_completion
               SET realization_photos_json = CAST(:photos AS jsonb), update_at = now()
             WHERE completion_id = :rid
            """,
            {"rid": report_id, "photos": json.dumps(photos)},
        )

    async def send(self, day_id: UUID | str, employee_id: str) -> Any:
        """
        Mengirim laporan harian (menandatangani oleh Leader).
        """
        return await self.fetchone(
            """
            UPDATE public.work_completion
               SET leader_signed_at = now(), update_at = now()
             WHERE daily_plan_id = :day AND leader_signer_id = CAST(:emp AS uuid)
               AND report_scope = 'DAILY' AND delete_at IS NULL
            RETURNING completion_id AS id
            """,
            {"day": day_id, "emp": employee_id},
        )

    async def day_info(self, day_id: UUID | str) -> Any:
        """
        Mendapatkan informasi dasar dari hari kerja.
        """
        return await self.fetchone(
            "SELECT d.work_date, d.site_name AS title, CAST(d.weekly_plan_id AS text) AS plan_id FROM public.work_plan_daily d WHERE d.daily_plan_id = :day",
            {"day": day_id},
        )

    # ── Dokumen laporan (A4) ──────────────────────────────────────────────────────────────────
    async def plan_header(self, plan_id: UUID | str) -> Any:
        """
        Mendapatkan metadata kop (header) rencana kerja untuk dokumen cetak.
        """
        return await self.fetchone(
            """
            SELECT
                'WP-W' || wp.week_number || '-' || wp.year AS number,
                wp.project_name AS title,
                '' AS location_text,
                'PROJECT' AS category,
                div.name AS unit_name,
                wp.start_date AS period_start,
                wp.end_date AS period_end,
                pm.full_name AS pm_name,
                ld.full_name AS leader_name
            FROM public.work_plan_weekly wp
            LEFT JOIN public.division div ON div.division_id = wp.division_id
            LEFT JOIN public.employee pm ON pm.employee_id = wp.approved_by_pm_id
            LEFT JOIN public.employee ld ON ld.employee_id = wp.created_by_id
            WHERE wp.weekly_plan_id = :plan
            """,
            {"plan": plan_id},
        )

    async def daily_report_doc(self, day_id: UUID | str) -> Any:
        """
        Mengambil keseluruhan isi laporan harian untuk hari tertentu.
        """
        return await self.fetchone(
            """
            SELECT
                d.work_date,
                d.site_name AS day_title,
                CASE
                    WHEN c.pm_signed_at IS NOT NULL THEN 'APPROVED'
                    WHEN c.leader_signed_at IS NOT NULL THEN 'SUBMITTED'
                    ELSE 'DRAFT'
                END AS status,
                c.summary_notes AS body,
                c.obstacles AS obstacle,
                false AS resubmitted,
                c.leader_signed_at AS submitted_at,
                c.pm_signed_at AS reviewed_at,
                'Laporan diverifikasi' AS review_note,
                se.full_name AS submitted_by_name,
                re.full_name AS reviewed_by_name,
                COALESCE(
                    ARRAY(
                        SELECT elem->>'url'
                        FROM jsonb_array_elements(c.realization_photos_json) AS elem
                    ),
                    '{}'
                ) AS evidence,
                COALESCE(
                    ARRAY(
                        SELECT wpi.title
                        FROM public.work_plan_item wpi
                        WHERE wpi.daily_plan_id = d.daily_plan_id AND wpi.delete_at IS NULL
                        ORDER BY wpi.create_at
                    ),
                    '{}'
                ) AS tasks
            FROM public.work_plan_daily d
            LEFT JOIN public.work_completion c ON c.daily_plan_id = d.daily_plan_id AND c.report_scope = 'DAILY' AND c.delete_at IS NULL
            LEFT JOIN public.employee se ON se.employee_id = c.leader_signer_id
            LEFT JOIN public.employee re ON re.employee_id = c.pm_signer_id
            WHERE d.daily_plan_id = :day
            ORDER BY c.create_at DESC LIMIT 1
            """,
            {"day": day_id},
        )

    async def weekly_report_doc(self, plan_id: UUID | str, name: str) -> Any:
        """
        Mengambil laporan mingguan lengkap dengan detail peninjau.
        """
        return await self.fetchone(
            """
            SELECT
                'Laporan Mingguan ' || wr.week_number AS name,
                wr.start_date AS starts_on,
                wr.end_date AS ends_on,
                CASE
                    WHEN c.pm_signed_at IS NOT NULL THEN 'APPROVED'
                    WHEN c.leader_signed_at IS NOT NULL THEN 'SUBMITTED'
                    ELSE 'DRAFT'
                END AS status,
                c.summary_notes AS body,
                c.obstacles AS obstacle,
                false AS resubmitted,
                'Laporan disetujui PM' AS review_note,
                se.full_name AS submitted_by_name,
                re.full_name AS reviewed_by_name
            FROM public.work_plan_weekly wr
            LEFT JOIN public.work_completion c ON c.weekly_plan_id = wr.weekly_plan_id AND c.report_scope = 'WEEKLY' AND c.delete_at IS NULL
            LEFT JOIN public.employee se ON se.employee_id = c.leader_signer_id
            LEFT JOIN public.employee re ON re.employee_id = c.pm_signer_id
            WHERE wr.weekly_plan_id = :plan
            ORDER BY c.create_at DESC LIMIT 1
            """,
            {"plan": plan_id},
        )

    async def plan_exports(self, plan_id: UUID | str) -> Sequence[Any]:
        """
        Daftar ekspor template dokumen (DOCX, PPTX, PDF, XLSX) milik SK/penyelesaian ini.
        """
        return await self.fetchall(
            """
            SELECT
                dte.export_id,
                dte.completion_id,
                dte.template_type,
                dte.master_template_path,
                dte.export_format,
                dte.file_output_url,
                dte.generated_by_id,
                dte.create_at
            FROM public.document_template_export dte
            JOIN public.work_completion wc ON wc.completion_id = dte.completion_id
            WHERE (wc.weekly_plan_id = :plan OR wc.daily_plan_id = :plan OR dte.completion_id = :plan)
              AND dte.delete_at IS NULL
            ORDER BY dte.create_at DESC
            """,
            {"plan": plan_id},
        )
