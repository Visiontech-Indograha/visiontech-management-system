"""P9-1 · Data SINTETIS untuk uji beban: satu organisasi, 60 pekerja lapangan + 1 PM, satu lokasi proyek.

Hanya untuk DB uji (nama berakhiran `_test`, dijaga `unsafe_test_database`). Tidak pernah ke prod.

    python -m tests.beban.seed_beban buat  <berkas-keluaran.json>   # buat & tulis daftar akun (tanpa sandi)
    python -m tests.beban.seed_beban hapus <berkas-keluaran.json>   # hapus organisasi uji beban

Sandi semua akun = env `BEBAN_PASSWORD` (diisi penguji, tidak disimpan di berkas mana pun).
Koneksi: `TEST_SETUP_DATABASE_URL` (superuser/pemilik) bila ada, selain itu `DATABASE_URL`.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from urllib.parse import urlparse

import psycopg2

from app.core.config import settings
from app.core.security import hash_password
from tests.db_guard import unsafe_test_database

FIELD_WORKERS = 60
SITE = (-6.2, 106.8)   # lat, lng; radius 150 m


def _conn() -> psycopg2.extensions.connection:
    url = os.environ.get("TEST_SETUP_DATABASE_URL") or settings.DATABASE_URL
    reason = unsafe_test_database(url)
    if reason:
        sys.exit(f"Ditolak: {reason}")
    u = urlparse(url.replace("+asyncpg", ""))
    conn = psycopg2.connect(host=u.hostname, port=u.port or 5432, user=u.username, password=u.password,
                            dbname=u.path.lstrip("/"))
    conn.autocommit = True
    return conn


def buat(out_path: str) -> None:
    password = os.environ.get("BEBAN_PASSWORD")
    if not password or len(password) < 12:
        sys.exit("Isi BEBAN_PASSWORD (minimal 12 karakter) untuk sandi akun uji beban.")
    tag = uuid.uuid4().hex[:8]
    pw_hash = hash_password(password)
    cur = _conn().cursor()
    cur.execute("INSERT INTO vms.organization (name) VALUES (%s) RETURNING id", (f"Uji beban {tag}",))
    org = cur.fetchone()[0]
    cur.execute("INSERT INTO vms.business_unit (organization_id, code, name) VALUES (%s, 'BEBAN', 'Unit uji beban') "
                "RETURNING id", (org,))
    unit = cur.fetchone()[0]
    cur.execute("INSERT INTO vms.site (organization_id, name, location, radius_m, unit_id) "
                "VALUES (%s, 'Lokasi uji beban', ST_GeogFromText(%s), 150, %s) RETURNING id",
                (org, f"POINT({SITE[1]} {SITE[0]})", unit))
    site = cur.fetchone()[0]

    def person(i: int, who: str, mode: str) -> tuple[str, str]:
        cur.execute("INSERT INTO vms.employee (organization_id, employee_no, full_name, position, unit_id, join_date, "
                    "attendance_mode) VALUES (%s, %s, %s, 'Teknisi', %s, '2026-01-05', %s) RETURNING id",
                    (org, f"BEBAN-{i:03d}", f"Pekerja uji beban {i:03d}", unit, mode))
        emp = cur.fetchone()[0]
        login = f"{who}-{tag}@beban.test"
        cur.execute("INSERT INTO vms.app_user (organization_id, login, password_hash, employee_id) "
                    "VALUES (%s, %s, %s, %s) RETURNING id", (org, login, pw_hash, emp))
        return login, cur.fetchone()[0]

    field = [person(i, f"lapangan{i:03d}", "FIELD")[0] for i in range(1, FIELD_WORKERS + 1)]
    pm_login, pm_user = person(0, "pm", "OFFICE")
    cur.execute("INSERT INTO vms.user_role (user_id, role, unit_id) VALUES (%s, 'PM', %s)", (pm_user, unit))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"tag": tag, "organization_id": str(org), "site_id": str(site), "site": {"lat": SITE[0],
                   "lng": SITE[1]}, "field": field, "pm": pm_login}, f, indent=1)
    print(f"Organisasi uji beban {tag}: {len(field)} pekerja lapangan + 1 PM, daftar akun: {out_path}")


def hapus(out_path: str) -> None:
    from tests.cleanup import purge_organization

    with open(out_path, encoding="utf-8") as f:
        data = json.load(f)
    conn = _conn()
    purge_organization(conn, data["organization_id"])
    conn.cursor().execute("DELETE FROM vms.login_attempt WHERE login LIKE %s", (f"%-{data['tag']}@beban.test",))
    print(f"Organisasi uji beban {data['tag']} dihapus.")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in {"buat", "hapus"}:
        sys.exit(__doc__)
    {"buat": buat, "hapus": hapus}[sys.argv[1]](sys.argv[2])
