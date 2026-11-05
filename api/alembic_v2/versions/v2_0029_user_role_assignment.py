"""Tabel `user_role_assignment` (peran ganda dan penugasan kantor, ADR 0002) - fase 1, hanya expand.

Expand-only: tabel baru + indeks + isi awal `source='PRIMARY'` dari data lama. Tidak mengubah atau
menghapus kolom lama (`users.system_role`, `employee.office_id`) dan tidak mengubah akses siapa pun
(kode lama tidak membaca tabel ini).

Isi awal (idempoten, ON CONFLICT DO NOTHING): untuk tiap user aktif (belum dihapus, is_active) dengan
peran fase 1:
- SUPER_ADMIN dan OPERATIONAL_MANAGER -> office_id NULL (semua kantor);
- ADMIN_HR_GA dan FINANCE -> office_id = employee.office_id (dilewati bila user tanpa karyawan/kantor,
  karena CHECK mewajibkan kantor).
Peran lain (PM, TEAM_LEADER, EMPLOYEE) belum dipetakan di fase 1 dan tidak diisi.

Indeks dibuat CONCURRENTLY (pola v2_0028); indeks INVALID sisa kegagalan dibuang dulu.

Revision ID: v2_0029
Revises: v2_0028
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2_0029"
down_revision: str | None = "v2_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UQ = "uq_user_role_assignment_active"
_IX_USER = "ix_user_role_assignment_user"
_IX_OFFICE_ROLE = "ix_user_role_assignment_office_role"
_NAMES = [_UQ, _IX_USER, _IX_OFFICE_ROLE]


def _drop_invalid() -> None:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT c.relname FROM pg_index x JOIN pg_class c ON c.oid = x.indexrelid "
            "WHERE NOT x.indisvalid AND c.relname = ANY(:n)"
        ),
        {"n": _NAMES},
    )
    for (name,) in rows.fetchall():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_role_assignment (
            assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(user_id),
            role system_role_enum NOT NULL,
            office_id UUID NULL REFERENCES office(office_id),
            source TEXT NOT NULL DEFAULT 'MANUAL',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES users(user_id),
            delete_at TIMESTAMPTZ NULL,
            delete_by UUID NULL REFERENCES users(user_id),
            CONSTRAINT ck_ura_source CHECK (source IN ('PRIMARY', 'MANUAL')),
            CONSTRAINT ck_ura_office CHECK (
                (office_id IS NULL AND role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER'))
                OR office_id IS NOT NULL
            )
        )
        """
    )
    with op.get_context().autocommit_block():
        _drop_invalid()
        op.execute(
            f"CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {_UQ} ON user_role_assignment "
            "(user_id, role, COALESCE(office_id, '00000000-0000-0000-0000-000000000000'::uuid)) "
            "WHERE delete_at IS NULL"
        )
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_IX_USER} ON user_role_assignment (user_id) "
            "WHERE delete_at IS NULL"
        )
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_IX_OFFICE_ROLE} ON user_role_assignment "
            "(office_id, role) WHERE delete_at IS NULL"
        )
    op.execute(
        """
        INSERT INTO user_role_assignment (user_id, role, office_id, source)
        SELECT u.user_id, u.system_role,
               CASE WHEN u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER') THEN NULL
                    ELSE e.office_id END,
               'PRIMARY'
        FROM users u
        LEFT JOIN employee e ON e.employee_id = u.employee_id
        WHERE u.delete_at IS NULL AND u.is_active
          AND u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'ADMIN_HR_GA', 'FINANCE')
          AND (u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER') OR e.office_id IS NOT NULL)
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name in _NAMES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")
    op.execute("DROP TABLE IF EXISTS user_role_assignment")
