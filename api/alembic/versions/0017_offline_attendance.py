"""Absensi lapangan luring (R-34, mengubah K-13): kunci perangkat, jejak peristiwa luring, kolom absensi luring.

- `attendance_device_key`: kunci publik EC P-256 dari Android Keystore per akun & perangkat. Setiap peristiwa
  absen luring ditandatangani kunci privatnya (tidak bisa dikeluarkan dari HP); server memverifikasi sehingga
  tanggal, jam, dan lokasi yang diubah di data aplikasi ditolak.
- `attendance_offline_event`: satu baris per `client_op_id` — idempoten saat antrean dikirim ulang.
- `attendance.offline`, `offline_note` (alasan perlu review: jam tak terverifikasi, terlambat sinkron > 24 jam,
  lokasi palsu), `check_out_requested_at` (absen pulang luring yang menunggu absen masuk disetujui).

Revision ID: 0017_offline_attendance
Revises: 0016_web_selfie_required
Create Date: 2026-10-02
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0017_offline_attendance"
down_revision: str | Sequence[str] | None = "0016_web_selfie_required"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute(
        """
        CREATE TABLE attendance_device_key (
          id              uuid PRIMARY KEY DEFAULT new_id(),
          organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
          user_id         uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
          device_id       text NOT NULL,
          public_key      text NOT NULL,
          created_at      timestamptz NOT NULL DEFAULT now(),
          revoked_at      timestamptz
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX attendance_device_key_active_uidx ON attendance_device_key (user_id, device_id) "
               "WHERE revoked_at IS NULL")
    op.execute(
        """
        CREATE TABLE attendance_offline_event (
          client_op_id    uuid PRIMARY KEY,
          organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
          user_id         uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
          kind            text NOT NULL CHECK (kind IN ('CHECK_IN','CHECK_OUT')),
          attendance_id   uuid,
          event_time      timestamptz NOT NULL,
          time_trusted    boolean NOT NULL,
          result          text NOT NULL,
          received_at     timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "ALTER TABLE attendance ADD COLUMN offline boolean NOT NULL DEFAULT false, "
        "ADD COLUMN offline_note text, ADD COLUMN check_out_requested_at timestamptz"
    )


def downgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute("ALTER TABLE attendance DROP COLUMN IF EXISTS check_out_requested_at, "
               "DROP COLUMN IF EXISTS offline_note, DROP COLUMN IF EXISTS offline")
    op.execute("DROP TABLE IF EXISTS attendance_offline_event")
    op.execute("DROP TABLE IF EXISTS attendance_device_key")
