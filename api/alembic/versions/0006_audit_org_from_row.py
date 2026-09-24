"""audit menemukan organisasi dari data baris, bukan hanya konteks sesi (V-15)

Tabel yang diaudit tanpa kolom `organization_id` (asset_allocation, plan_change, plan_document,
employee_document) sebelumnya memakai `current_org_id()`: tanpa konteks → `audit_event.organization_id`
NULL (NOT NULL, operasi gagal); konteks salah → tercatat di organisasi lain. Kini organisasi diambil
dari baris yang dirujuk (work_plan, employee, asset); konteks sesi hanya cadangan terakhir.

Revision ID: 0006_audit_org_from_row
Revises: 0005_plan_document_immutable
Create Date: 2026-09-24
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0006_audit_org_from_row"
down_revision: str | Sequence[str] | None = "0005_plan_document_immutable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TEMPLATE = """
CREATE OR REPLACE FUNCTION vms.tg_audit_row() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  v_row jsonb;
  v_org uuid;
  v_plan uuid;
  v_changes jsonb;
BEGIN
  -- COALESCE tidak dapat dipakai pada tipe record, jadi barisnya dipilih eksplisit.
  v_row := CASE WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;
  v_plan := NULLIF(v_row ->> 'work_plan_id', '')::uuid;
{org}

  IF TG_OP = 'UPDATE' THEN
    SELECT jsonb_object_agg(key, jsonb_build_object('dari', old_value, 'menjadi', new_value))
      INTO v_changes
    FROM (
      SELECT o.key, o.value AS old_value, n.value AS new_value
      FROM jsonb_each(to_jsonb(OLD)) o
      JOIN jsonb_each(to_jsonb(NEW)) n USING (key)
      WHERE o.value IS DISTINCT FROM n.value
    ) diff;
  END IF;

  INSERT INTO audit_event (organization_id, actor_user_id, actor_label, action, entity_type, entity_id, work_plan_id, changes)
  VALUES (
    v_org,
    current_user_id(),
    COALESCE(current_setting('app.actor_label', true), 'sistem'),
    TG_OP,
    TG_TABLE_NAME,
    (v_row ->> 'id')::uuid,
    v_plan,
    v_changes
  );
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;
"""

_FROM_ROW = """  -- Organisasi dari data baris itu sendiri; konteks sesi hanya cadangan terakhir (V-15).
  v_org := COALESCE(
    NULLIF(v_row ->> 'organization_id', '')::uuid,
    (SELECT wp.organization_id FROM work_plan wp WHERE wp.id = v_plan),
    (SELECT e.organization_id FROM employee e WHERE e.id = NULLIF(v_row ->> 'employee_id', '')::uuid),
    (SELECT a.organization_id FROM asset a WHERE a.id = NULLIF(v_row ->> 'asset_id', '')::uuid),
    current_org_id()
  );"""

_FROM_CONTEXT = "  v_org := COALESCE(v_row ->> 'organization_id', current_org_id()::text)::uuid;"


def _apply(org_block: str) -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute(_TEMPLATE.replace("{org}", org_block))


def upgrade() -> None:
    _apply(_FROM_ROW)


def downgrade() -> None:
    _apply(_FROM_CONTEXT)
