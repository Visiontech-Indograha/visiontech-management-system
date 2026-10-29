"""
Pembantu uji daily-first (Milestone 5): jadwal harian dunia uji tanpa melewati UI.
Menggantikan `run_plan_to_in_progress` / `create_draft_plan` alur SK V1 yang dipensiunkan.
"""
from __future__ import annotations

import io
from datetime import timedelta

from PIL import Image

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


def add_item(plan_id: str, world: World, title: str = "Titik uji", **cols: object) -> str:
    """Satu item (pekerjaan) pada jadwal harian; kolom tambahan lewat `cols` (mis. status, task_phase)."""
    wt = str(sync_query("INSERT INTO work_type (division_id, name) VALUES (%s, %s) RETURNING work_type_id",
                        (world.unit_id, f"Pekerjaan uji {world.tag} {title}"))[0][0])
    fields = {"status": "TODO", "task_phase": "INSTALLATION", "is_main_deliverable": True, **cols}
    names = ", ".join(["daily_plan_id", "work_type_id", "title", *fields])
    marks = ", ".join(["%s"] * (3 + len(fields)))
    return str(sync_query(f"INSERT INTO work_plan_item ({names}) VALUES ({marks}) RETURNING item_id",
                          (plan_id, wt, title, *fields.values()))[0][0])


def check_in(client, world: World, who: str) -> None:
    """Absen masuk di luar radius dengan penjelasan (tercatat, menunggu peninjauan) — cukup untuk 'sudah absen'."""
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (7, 77, 177)).save(buf, "PNG")
    selfie = client.post("/files/upload", headers=world.headers(client, who),
                         files={"file": ("swafoto.png", buf.getvalue(), "image/png")})
    assert selfie.status_code == 200, selfie.text
    body = {"site_id": world.site_id, "location": {"lat": -6.3, "lng": 106.8}, "channel": "MOBILE",
            "selfie_file_id": selfie.json()["file_id"], "explanation": "Pengecekan lokasi"}
    response = client.post("/attendance/check-in", headers=world.headers(client, who), json=body)
    assert response.status_code == 200, response.text
