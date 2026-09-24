"""dokumen terbit terkunci penuh: semua kolom isi + penerimaan sekali tulis (R4)

`tg_plan_document_immutable` hanya menjaga 6 kolom. Yang lolos: `snapshot_sha256` (dipakai
`verify_signature_qr` — mengubahnya mengecoh verifikasi QR), `work_plan_id` (dokumen dipindah ke SK
lain), `reason`, serta `accepted_by`/`accepted_at` yang bisa ditimpa setelah SK diterima.
Kini hanya `status` yang boleh berubah bebas; pencatatan penerimaan hanya sekali (dari NULL).

Revision ID: 0005_plan_document_immutable
Revises: 0004_member_active_upper_inf
Create Date: 2026-09-24
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0005_plan_document_immutable"
down_revision: str | Sequence[str] | None = "0004_member_active_upper_inf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = """
CREATE OR REPLACE FUNCTION vms.tg_plan_document_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  -- Isi dokumen terbit tidak pernah berubah; hanya siklusnya (status) yang bergerak.
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.work_plan_id IS DISTINCT FROM OLD.work_plan_id
     OR NEW.kind IS DISTINCT FROM OLD.kind
     OR NEW.version IS DISTINCT FROM OLD.version
     OR NEW.number IS DISTINCT FROM OLD.number
     OR NEW.snapshot IS DISTINCT FROM OLD.snapshot
     OR NEW.snapshot_sha256 IS DISTINCT FROM OLD.snapshot_sha256
     OR NEW.reason IS DISTINCT FROM OLD.reason
     OR NEW.issued_by IS DISTINCT FROM OLD.issued_by
     OR NEW.issued_at IS DISTINCT FROM OLD.issued_at
     -- penerimaan dicatat sekali: dari kosong ke terisi, tidak ditimpa sesudahnya
     OR (OLD.accepted_by IS NOT NULL AND NEW.accepted_by IS DISTINCT FROM OLD.accepted_by)
     OR (OLD.accepted_at IS NOT NULL AND NEW.accepted_at IS DISTINCT FROM OLD.accepted_at) THEN
    RAISE EXCEPTION 'Dokumen terbit bersifat tetap. Terbitkan versi baru, jangan mengubah versi lama.'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
"""

_OLD = """
CREATE OR REPLACE FUNCTION vms.tg_plan_document_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.snapshot IS DISTINCT FROM OLD.snapshot
     OR NEW.number IS DISTINCT FROM OLD.number
     OR NEW.version IS DISTINCT FROM OLD.version
     OR NEW.kind IS DISTINCT FROM OLD.kind
     OR NEW.issued_by IS DISTINCT FROM OLD.issued_by
     OR NEW.issued_at IS DISTINCT FROM OLD.issued_at THEN
    RAISE EXCEPTION 'Dokumen terbit bersifat tetap. Terbitkan versi baru, jangan mengubah versi lama.'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
"""


def upgrade() -> None:
    op.execute(_NEW)


def downgrade() -> None:
    op.execute(_OLD)
