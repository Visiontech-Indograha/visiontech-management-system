"""
Pembantu uji daily-first (Milestone 5): jadwal harian dunia uji tanpa melewati UI.
Menggantikan `run_plan_to_in_progress` / `create_draft_plan` alur SK V1 yang dipensiunkan.
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, sync_query


def make_daily_plan(world: World, *, status: str = "APPROVED", days_from_today: int = 0,
                    team_id: str | None = None) -> str:
    """Jadwal harian tim dunia uji pada tanggal relatif hari ini (WIB) dengan status tertentu."""
    work_date = jakarta_now().date() + timedelta(days=days_from_today)
    return str(sync_query(
        """
        INSERT INTO work_plan_daily (division_id, team_id, work_date, site_name, site_lat, site_lng, status,
                                     created_by_id, approved_by_pm_id, approved_at)
        VALUES (%s, %s, %s, 'Site uji', -6.2000000, 106.8000000, %s, %s,
                CASE WHEN %s IN ('APPROVED', 'ONGOING', 'COMPLETED') THEN %s::uuid END,
                CASE WHEN %s IN ('APPROVED', 'ONGOING', 'COMPLETED') THEN now() END)
        RETURNING daily_plan_id
        """,
        (world.unit_id, team_id or world.team_id, work_date, status, world.employees["pm"],
         status, world.employees["pm"], status))[0][0])


def run_daily_to_ongoing(world: World) -> str:
    """Jadwal hari ini yang sedang berjalan (ONGOING) — padanan SK IN_PROGRESS."""
    return make_daily_plan(world, status="ONGOING")
