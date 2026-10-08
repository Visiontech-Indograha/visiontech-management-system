"""Foto contoh pada slot template foto (Rencana Kerja v3, permintaan pemilik 2026-10-09).

Revision ID: 0030_work_type_photo_example
Revises: 0029_work_type_photo
Create Date: 2026-10-09

`work_type_photo.example_file_id`: berkas foto contoh yang diunggah PM untuk satu slot, tampil di web & HP agar
ketua/anggota tahu foto yang diharapkan. Opsional; berkas tetap milik organisasi yang sama.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0030_work_type_photo_example"
down_revision: str | None = "0029_work_type_photo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE vms.work_type_photo ADD COLUMN IF NOT EXISTS example_file_id uuid "
               "REFERENCES vms.file_object(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE vms.work_type_photo DROP COLUMN IF EXISTS example_file_id")
