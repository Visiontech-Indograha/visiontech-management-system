"""GET /attendance mode keyset: kursor rusak 422, mode lama utuh, halaman tanpa duplikat/lompat, cakupan tetap."""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _seed(world: World, n: int) -> set[str]:
    """n absensi; dua karyawan di tanggal dan jam masuk SAMA (uji tie-break tiga kolom)."""
    ids: set[str] = set()
    for i in range(n):
        who = ("member", "leader")[i % 2]
        row = sync_query(
            "INSERT INTO attendance (employee_id, attendance_date, target_location_type, office_id, scheduled_in, "
            "scheduled_out, clock_in_at, in_lat, in_lng, face_match_score, face_photo_path, distance_to_target_m, "
            "is_within_attendance_radius, distance_from_main_office_m, city_zone_status, meal_allowance_amount) "
            "VALUES (%s, DATE '2099-01-01' + %s, 'OFFICE', %s, '08:00', '17:00', TIMESTAMPTZ '2026-01-01 01:00+00', "
            "-6.2, 106.8, 99, 'x', 0, TRUE, 0, 'DALAM_KOTA', 0) RETURNING attendance_id",
            (world.employees[who], i // 2, world.site_id),
        )
        ids.add(str(row[0][0]))
    return ids


def test_bad_cursor_and_old_mode(client, world: World):
    headers = world.headers(client, "ops")
    assert client.get("/attendance", headers=headers, params={"cursor": "rusak!!"}).status_code == 422
    old = client.get("/attendance", headers=headers)
    assert old.status_code == 200 and "x-next-cursor" not in old.headers and "total" in old.json()


def test_pages_without_duplicates_and_scope(client, world: World):
    ids = _seed(world, 5)
    seen, cursor = [], ""
    for _ in range(10):
        r = client.get("/attendance", headers=world.headers(client, "ops"),
                       params={"cursor": cursor, "size": 2})
        assert r.status_code == 200, r.text
        assert r.json()["total"] == 0
        seen += [row["id"] for row in r.json()["items"]]
        cursor = r.headers.get("x-next-cursor", "")
        if not cursor:
            break
    assert len(seen) == len(set(seen)) and ids <= set(seen)
    # Cakupan tidak melebar: anggota biasa hanya melihat miliknya sendiri di mode keyset.
    mine = client.get("/attendance", headers=world.headers(client, "member"), params={"cursor": "", "size": 200})
    assert mine.status_code == 200
    assert {row["employee_id"] for row in mine.json()["items"]} <= {world.employees["member"]}
