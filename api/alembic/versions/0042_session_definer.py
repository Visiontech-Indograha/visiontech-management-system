"""Pulihkan SECURITY DEFINER pada fungsi sesi (koreksi migrasi 0041).

Revision ID: 0042_session_definer
Revises: 0041_session_and_device_limit
Create Date: 2026-10-14

Konteks: migrasi 0041 membuat ulang rotate_session/issue_session/count_active_devices
dengan ``CREATE OR REPLACE FUNCTION`` TANPA atribut ``SECURITY DEFINER``, sehingga
atribut yang semula dipasang oleh loop ``ALTER FUNCTION ... SECURITY DEFINER`` di
``db/05_face.sql`` hilang begitu 0041 dijalankan (``CREATE OR REPLACE`` mengembalikan
fungsi ke SECURITY INVOKER bawaan).

Akibatnya fungsi berjalan sebagai peran runtime ``vms_api`` di bawah RLS
``session_visibility (user_id = current_user_id())``. Saat refresh token,
``current_user_id()`` belum terisi (identitas belum diketahui) sehingga baris sesi
tersaring → ``NOT FOUND`` → 401 — login sukses, refresh halaman langsung terlempar
ke login.

Perbaikan di sini idempoten dan aman untuk semua basis data: DB segar yang membangun
skema dari ``db/*.sql`` sudah mendapat SECURITY DEFINER dari loop 05_face.sql, jadi
``ALTER FUNCTION`` berikut tidak mengubah apa pun. DB yang sudah menjalankan 0041
lama (termasuk produksi) dipulihkan.

Catatan: 0041 juga diperbaiki di tempat (deklarasi SECURITY DEFINER eksplisit) untuk
instalasi baru; migrasi ini menutup basis data yang terlanjur termigrasi.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0042_session_definer"
down_revision: str | None = "0041_session_and_device_limit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for fn in (
        "vms.rotate_session(text, inet, text)",
        "vms.issue_session(uuid, uuid, text, text, inet, text, interval)",
        "vms.count_active_devices(uuid)",
    ):
        op.execute(f"ALTER FUNCTION {fn} SECURITY DEFINER SET search_path = vms, public;")


def downgrade() -> None:
    # Tidak ada perilaku yang perlu dibalik: atribut keamanan fungsi.
    pass
