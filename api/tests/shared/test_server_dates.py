"""
V-10 · Tanggal dari server (CLAUDE.md aturan 3 "jangan percaya perangkat", dok 07 R6).
"Hari ini" = tanggal menurut zona waktu organisasi (`organization.timezone`), dihitung dari jam
server — bukan jam perangkat, bukan tanggal kiriman klien, bukan zona waktu mesin (Docker = UTC).
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import requires_db, sync_query

_CLOCK = re.compile(r"datetime\.(now|utcnow)\(|date\.today\(|time\.time\(")


def test_clock_is_read_only_in_core_time():
    """Standar backend: waktu hanya lewat core/time.py."""
    offenders = [
        f"{path.as_posix()}:{n}"
        for path in Path("app").rglob("*.py") if path.as_posix() != "app/core/time.py"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if _CLOCK.search(line)
    ]
    assert offenders == []


@requires_db
def test_attendance_work_date_follows_the_organisation_timezone(client, world, fake_storage):
    # V2: absen wajib swafoto; tanggal kerja disimpan di attendance.attendance_date.
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (90, 90, 90)).save(buf, "PNG")
    headers = world.headers(client, "member")
    selfie = client.post("/files/upload", headers=headers, files={"file": ("s.png", buf.getvalue(), "image/png")})
    response = client.post("/attendance/check-in", headers=headers, json={
        "site_id": world.site_id, "location": {"lat": -6.2, "lng": 106.8},
        "selfie_file_id": selfie.json()["file_id"]})

    assert response.status_code == 200, response.text
    assert sync_query("SELECT attendance_date FROM attendance WHERE attendance_id = %s",
                      (response.json()["id"],)) == [(jakarta_now().date(),)]
