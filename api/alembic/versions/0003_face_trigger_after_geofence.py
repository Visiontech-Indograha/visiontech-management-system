"""wajah tidak cocok → NEEDS_REVIEW: trigger wajah berjalan setelah geofence

PostgreSQL menjalankan trigger BEFORE menurut urutan nama. `attendance_face_flag` berjalan
sebelum `attendance_geofence`, lalu geofence menyetel ulang status berdasarkan jarak sehingga
hasil NO_MATCH/LOW_QUALITY selalu tertimpa menjadi AUTO_VALID. Nama baru diurutkan setelah
`attendance_geofence`. Pada tabel berpartisi, RENAME juga berlaku ke partisinya.

Revision ID: 0003_face_after_geofence
Revises: 0002_fix_new_id
Create Date: 2026-09-23
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0003_face_after_geofence"
down_revision: str | Sequence[str] | None = "0002_fix_new_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TRIGGER attendance_face_flag ON vms.attendance RENAME TO attendance_post_geofence_face_flag")


def downgrade() -> None:
    op.execute("ALTER TRIGGER attendance_post_geofence_face_flag ON vms.attendance RENAME TO attendance_face_flag")
