"""Seed jenis dokumen awal untuk pengingat dokumen kendaraan (data saja, idempoten).

Revision ID: v2_0042
Revises: v2_0041
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0042"
down_revision: str | None = "v2_0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KODE = ("STNK", "KIR", "PAJAK", "PAJAK_5TH", "SIM", "ASURANSI")


def upgrade() -> None:
    # Ambang bawaan kolom (30, 21, 14 hari; harian mulai H-7). ON CONFLICT: aman diulang, tidak menimpa ubahan operator.
    op.execute(
        """
        INSERT INTO document_type (code, nama, berlaku_untuk) VALUES
            ('STNK', 'STNK', 'KENDARAAN'),
            ('KIR', 'KIR', 'KENDARAAN'),
            ('PAJAK', 'Pajak tahunan', 'KENDARAAN'),
            ('PAJAK_5TH', 'Pajak 5 tahunan', 'KENDARAAN'),
            ('SIM', 'SIM', 'KARYAWAN'),
            ('ASURANSI', 'Asuransi', 'KENDARAAN')
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    # Hanya baris seed yang belum dipakai dokumen; jenis yang sudah dipakai dibiarkan (FK).
    codes = ", ".join(f"'{c}'" for c in _KODE)
    op.execute(
        f"""
        DELETE FROM document_type dt WHERE dt.code IN ({codes})
        AND NOT EXISTS (SELECT 1 FROM vehicle_document vd WHERE vd.doc_type_code = dt.code)
        """
    )
