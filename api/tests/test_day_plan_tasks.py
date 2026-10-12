"""
V-23 · SAVE_DAY & TOGGLE_TASK (`domain.js`).
- SAVE_DAY: PM unit/OPS, SK DRAFT; judul hari + 1..30 tugas (semua berjudul) menggantikan rincian hari.
  PUT /work-plans/{id}/days/{day_id}/plan  {"title", "tasks": [{"title"}]}
- TOGGLE_TASK: ketua menurut SK, SK IN_PROGRESS, tanggal hari sudah tiba, laporan hari itu masih
  DRAFT/CHANGES_REQUESTED (atau belum dibuat). POST /work-plans/{id}/days/{day_id}/tasks/{task_id}/toggle
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import create_draft_plan, run_plan_to_in_progress

pytestmark = requires_db


def _save_day(client, world: World, plan_id: str, day_id: str, who: str = "pm", **body):
    return client.put(f"/work-plans/{plan_id}/days/{day_id}/plan", headers=world.headers(client, who), json=body)


def _tasks(day_id: str) -> list[tuple]:
    return sync_query("SELECT title, is_done FROM vms.work_plan_task WHERE work_plan_day_id = %s ORDER BY sort_order",
                      (day_id,))


def _toggle(client, world: World, plan_id: str, day_id: str, task_id: str, who: str = "leader"):
    return client.post(f"/work-plans/{plan_id}/days/{day_id}/tasks/{task_id}/toggle",
                       headers=world.headers(client, who), json={})


def _first_task(day_id: str) -> str:
    return str(sync_query("SELECT id FROM vms.work_plan_task WHERE work_plan_day_id = %s ORDER BY sort_order LIMIT 1",
                          (day_id,))[0][0])


# ── SAVE_DAY ──────────────────────────────────────────────────────────────────────────────────
def test_pm_replaces_the_day_plan_of_a_draft(client, world):
    plan_id, day_ids = create_draft_plan(client, world)

    response = _save_day(client, world, plan_id, day_ids[0], title="Instalasi kamera lantai 2",
                         tasks=[{"title": "Tarik kabel"}, {"title": "Pasang kamera"}])

    assert response.status_code == 200, response.text
    assert sync_query("SELECT title FROM vms.work_plan_day WHERE id = %s", (day_ids[0],)) \
        == [("Instalasi kamera lantai 2",)]
    assert _tasks(day_ids[0]) == [("Tarik kabel", False), ("Pasang kamera", False)]


def test_save_day_rules(client, world):
    plan_id, day_ids = create_draft_plan(client, world)
    day = day_ids[0]

    empty = _save_day(client, world, plan_id, day, title="Hari 1", tasks=[])
    assert empty.status_code == 422 and empty.json()["error"]["message"] == "Isi antara 1 sampai 30 tugas per hari."
    many = _save_day(client, world, plan_id, day, title="Hari 1", tasks=[{"title": f"T{i}"} for i in range(31)])
    assert many.status_code == 422
    blank = _save_day(client, world, plan_id, day, title="Hari 1", tasks=[{"title": " "}])
    assert blank.status_code == 422 and blank.json()["error"]["message"] == "Judul hari dan setiap tugas wajib diisi."
    assert _save_day(client, world, plan_id, day, who="member", title="X", tasks=[{"title": "Y"}]).status_code == 404
    assert _tasks(day) == [("Pasang kamera", False)]                    # tidak berubah


def test_day_plan_is_locked_once_published(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)

    response = _save_day(client, world, plan_id, day_ids[0], title="Ubah", tasks=[{"title": "Baru"}])

    assert response.status_code == 409 and response.json()["error"]["code"] == "INVALID_STATE"


# ── TOGGLE_TASK ───────────────────────────────────────────────────────────────────────────────
def test_leader_toggles_a_task_on_a_running_plan(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    task = _first_task(day_ids[0])

    done = _toggle(client, world, plan_id, day_ids[0], task)
    assert done.status_code == 200, done.text
    assert sync_query("SELECT is_done, done_at IS NOT NULL, done_by IS NOT NULL FROM vms.work_plan_task "
                      "WHERE id = %s", (task,)) == [(True, True, True)]
    undone = _toggle(client, world, plan_id, day_ids[0], task)
    assert undone.status_code == 200
    assert sync_query("SELECT is_done, done_at IS NULL FROM vms.work_plan_task WHERE id = %s", (task,)) \
        == [(False, True)]


def test_toggle_rules(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    today_task, tomorrow_task = _first_task(day_ids[0]), _first_task(day_ids[1])
    leader = world.headers(client, "leader")

    assert _toggle(client, world, plan_id, day_ids[0], today_task, who="member").status_code == 403
    future = _toggle(client, world, plan_id, day_ids[1], tomorrow_task)
    assert future.status_code == 422
    assert future.json()["error"]["message"] == "Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan."
    assert _toggle(client, world, plan_id, day_ids[0], tomorrow_task).status_code == 404   # tugas hari lain

    assert client.put(f"/work-plans/{plan_id}/days/{day_ids[0]}", headers=leader,
                      json={"body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada"}).status_code == 200
    assert client.post(f"/work-plans/{plan_id}/days/{day_ids[0]}/submit", headers=leader).status_code == 200
    locked = _toggle(client, world, plan_id, day_ids[0], today_task)
    assert locked.status_code == 409
    assert locked.json()["error"]["message"] == "Daftar tugas tidak dapat diubah setelah laporan diserahkan."
