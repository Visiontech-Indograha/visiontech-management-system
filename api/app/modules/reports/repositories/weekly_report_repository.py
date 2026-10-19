"""
app/crud/crud_weekly_report.py
Laporan mingguan rencana kerja (work_plan_weekly & work_completion) untuk Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_WEEKS = """
    SELECT
        wpw.week_number AS week,
        'Laporan Mingguan ' || wpw.week_number AS name,
        wpw.start_date AS starts_on,
        wpw.end_date AS ends_on,
        COALESCE(bool_and(wpi.progress_percent >= 100), true) AS days_approved,
        CASE
            WHEN wc.pm_signed_at IS NOT NULL THEN 'APPROVED'
            WHEN wc.leader_signed_at IS NOT NULL THEN 'SUBMITTED'
            WHEN wpw.status = 'COMPLETED' THEN 'APPROVED'
            ELSE 'DRAFT'
        END AS status,
        COALESCE(wc.summary_notes, 'Laporan progres mingguan week ' || wpw.week_number) AS body,
        COALESCE(wc.obstacles, '') AS obstacle,
        CASE WHEN wc.pm_signed_at IS NOT NULL THEN 'Telah disetujui PM' ELSE NULL END AS review_note,
        false AS resubmitted
    FROM public.work_plan_weekly wpw
    LEFT JOIN public.work_plan_item wpi
        ON wpi.weekly_plan_id = wpw.weekly_plan_id AND wpi.delete_at IS NULL
    LEFT JOIN public.work_completion wc
        ON wc.weekly_plan_id = wpw.weekly_plan_id AND wc.report_scope = 'WEEKLY' AND wc.delete_at IS NULL
    WHERE wpw.delete_at IS NULL
      AND (CAST(:plan AS uuid) IS NULL OR wpw.weekly_plan_id = CAST(:plan AS uuid))
      AND (CAST(:week AS integer) IS NULL OR wpw.week_number = CAST(:week AS integer))
    GROUP BY wpw.weekly_plan_id, wpw.week_number, wpw.start_date, wpw.end_date, wpw.status,
             wc.pm_signed_at, wc.leader_signed_at, wc.summary_notes, wc.obstacles
    ORDER BY wpw.week_number
"""


class WeeklyReportRepository(BaseRepository):
    """Repositori rekapitulasi laporan berkala pekerjaan."""
    """
    CRUD untuk mengelola laporan mingguan (weekly report).
    Memungkinkan pengambilan jadwal per minggu dan pembaruan laporan (simpan/ajukan/review).
    """

    async def list_weeks(self, plan_id: UUID | str) -> list[Any]:
        """
        Mengambil daftar lengkap laporan per minggu untuk suatu rencana kerja.

        Args:
            plan_id (UUID | str): ID rencana kerja mingguan (weekly_plan_id).

        Returns:
            list[Any]: Daftar record tiap minggu beserta status pelaporan.
        """
        return list(await self.fetchall(_WEEKS, {"plan": plan_id, "week": None}))

    async def get_week(self, plan_id: UUID | str, week: int) -> Any:
        """
        Mengambil data spesifik untuk satu minggu laporan.

        Args:
            plan_id (UUID | str): ID rencana kerja.
            week (int): Nomor urut minggu.

        Returns:
            Any: Record laporan untuk minggu yang diminta.
        """
        return await self.fetchone(_WEEKS, {"plan": plan_id, "week": week})

    async def save(self, plan_id: UUID | str, week: Any, body: str, obstacle: str) -> Any:
        """
        Menyimpan draf laporan mingguan. Laporan yang sudah diajukan tidak akan terpengaruh.

        Args:
            plan_id (UUID | str): ID rencana kerja.
            week (Any): Record minggu yang akan disimpan.
            body (str): Isi laporan utama.
            obstacle (str): Kendala yang dihadapi.

        Returns:
            Any: Record yang menyimpan ID laporan mingguan (jika berhasil).
        """
        existing = await self.scalar(
            """
            SELECT completion_id FROM public.work_completion
            WHERE weekly_plan_id = :plan AND report_scope = 'WEEKLY' AND delete_at IS NULL
            """,
            {"plan": plan_id},
        )
        if existing:
            return await self.fetchone(
                """
                UPDATE public.work_completion
                   SET summary_notes = :body, obstacles = :obs, update_at = now()
                 WHERE completion_id = :cid
                RETURNING completion_id AS id
                """,
                {"cid": existing, "body": body, "obs": obstacle},
            )
        else:
            return await self.fetchone(
                """
                INSERT INTO public.work_completion (
                    report_scope, weekly_plan_id, summary_notes, obstacles,
                    realization_photos_json, leader_signer_id, signature_hash
                )
                VALUES (
                    'WEEKLY', :plan, :body, :obs,
                    '[]'::jsonb,
                    (SELECT created_by_id FROM public.work_plan_weekly WHERE weekly_plan_id = :plan),
                    md5(random()::text || clock_timestamp()::text)
                )
                RETURNING completion_id AS id
                """,
                {"plan": plan_id, "body": body, "obs": obstacle},
            )

    async def submit(self, plan_id: UUID | str, name: str, user_id: UUID | str) -> Any:
        """
        Mengajukan draf laporan mingguan agar bisa di-review oleh Project Manager.

        Args:
            plan_id (UUID | str): ID rencana kerja.
            name (str): Nama laporan mingguan.
            user_id (UUID | str): ID pengguna yang melakukan submit.

        Returns:
            Any: Record berisi ID laporan yang diajukan.
        """
        return await self.fetchone(
            """
            UPDATE public.work_completion
               SET leader_signer_id = (SELECT employee_id FROM public.users WHERE user_id = :uid),
                   leader_signed_at = now(),
                   update_at = now()
             WHERE weekly_plan_id = :plan AND report_scope = 'WEEKLY' AND delete_at IS NULL
            RETURNING completion_id AS id
            """,
            {"plan": plan_id, "uid": user_id},
        )

    async def review(self, plan_id: UUID | str, name: str, status: str, note: str | None, user_id: UUID | str) -> Any:
        """
        Menyimpan hasil review (setuju atau revisi) laporan mingguan oleh Project Manager.

        Args:
            plan_id (UUID | str): ID rencana kerja.
            name (str): Nama laporan mingguan.
            status (str): Status hasil review (misal: APPROVED, CHANGES_REQUESTED).
            note (str | None): Catatan review (opsional).
            user_id (UUID | str): ID pengguna yang me-review.

        Returns:
            Any: Record berisi ID laporan yang di-review.
        """
        if status == "APPROVED":
            return await self.fetchone(
                """
                UPDATE public.work_completion
                   SET pm_signer_id = (SELECT employee_id FROM public.users WHERE user_id = :uid),
                       pm_signed_at = now(),
                       update_at = now()
                 WHERE weekly_plan_id = :plan AND report_scope = 'WEEKLY' AND delete_at IS NULL
                RETURNING completion_id AS id
                """,
                {"plan": plan_id, "uid": user_id},
            )
        else:
            return await self.fetchone(
                """
                UPDATE public.work_completion
                   SET pm_signed_at = NULL,
                       obstacles = COALESCE(obstacles, '') || E'\n[Catatan Revisi PM]: ' || :note,
                       update_at = now()
                 WHERE weekly_plan_id = :plan AND report_scope = 'WEEKLY' AND delete_at IS NULL
                RETURNING completion_id AS id
                """,
                {"plan": plan_id, "note": note or ""},
            )


# Alias backward compatibility
CRUDWeeklyReport = WeeklyReportRepository
