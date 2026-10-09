"""
app/crud/crud_plan_revision.py
Riwayat revisi rencana kerja oleh PM (T6) dan dokumen versi baru hasil revisi. Hanya SQL, tanpa aturan bisnis.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.core.enums import DocumentKind, DocumentStatus

from .base import CRUDBase


class CRUDPlanRevision(CRUDBase):
    """Akses data tabel `vms.plan_revision` dan dokumen revisi."""

    async def insert_revision(self, org_id: UUID | str, plan_id: UUID | str, revision: int, revised_by: str,
                              reason: str, diff: list[dict[str, Any]], resolved_change_id: UUID | str | None) -> None:
        """Menambah satu baris riwayat revisi (insert-only)."""
        await self.execute(
            """
            INSERT INTO vms.plan_revision (organization_id, work_plan_id, revision, revised_by, reason, diff,
                                           resolved_change_id)
            VALUES (CAST(:org AS uuid), CAST(:plan AS uuid), :rev, CAST(:by AS uuid), :reason,
                    CAST(:diff AS jsonb), CAST(:change AS uuid))
            """,
            {"org": str(org_id), "plan": str(plan_id), "rev": revision, "by": revised_by, "reason": reason,
             "diff": json.dumps(diff, default=str, ensure_ascii=False),
             "change": str(resolved_change_id) if resolved_change_id else None},
        )

    async def list_revisions(self, plan_id: UUID | str) -> list[Any]:
        """Riwayat revisi satu rencana kerja, terbaru dulu."""
        return list(await self.fetchall(
            """
            SELECT r.id, r.revision, e.full_name AS revised_by_name, r.reason, r.diff, r.created_at
            FROM vms.plan_revision r LEFT JOIN vms.employee e ON e.id = r.revised_by
            WHERE r.work_plan_id = :plan
            ORDER BY r.revision DESC
            """,
            {"plan": plan_id},
        ))

    async def supersede_awaiting(self, plan_id: UUID | str) -> None:
        """Dokumen yang masih menunggu penerimaan ketua menjadi Tidak berlaku (digantikan versi revisi)."""
        await self.execute(
            "UPDATE vms.plan_document SET status = CAST(:superseded AS vms.document_status) "
            "WHERE work_plan_id = :plan AND status = CAST(:awaiting AS vms.document_status)",
            {"plan": plan_id, "superseded": DocumentStatus.SUPERSEDED, "awaiting": DocumentStatus.AWAITING_ACCEPTANCE},
        )

    async def issue_revision_document(self, plan_id: UUID | str, version: int, snapshot: dict[str, Any],
                                      issued_by: str, reason: str, status: DocumentStatus) -> None:
        """Dokumen versi baru. `EFFECTIVE` = langsung berlaku (setelah ketua menerima); `AWAITING_ACCEPTANCE` =
        ketua masih harus menerima sekali. Nomor = nomor rencana kerja + /REV-n."""
        await self.execute(
            """
            INSERT INTO vms.plan_document (work_plan_id, kind, version, number, status, snapshot, snapshot_sha256,
                                           reason, issued_by)
            SELECT id, CAST(:kind AS vms.document_kind), :version, number || '/REV-' || (:version - 1),
                   CAST(:status AS vms.document_status), CAST(:snapshot AS jsonb), ''::bytea, :reason, :issued_by
            FROM vms.work_plan WHERE id = :plan
            """,
            {"plan": plan_id, "kind": DocumentKind.REVISION, "version": version, "status": status,
             "snapshot": json.dumps(snapshot, default=str), "reason": reason, "issued_by": issued_by},
        )

    async def clear_appeal(self, plan_id: UUID | str) -> None:
        """Permintaan revisi dari ketua (status Revisi diminta) dianggap terjawab: alasan dikosongkan."""
        await self.execute("UPDATE vms.work_plan SET appeal_reason = NULL WHERE id = :plan", {"plan": plan_id})

    async def employee_name(self, employee_id: UUID | str) -> str | None:
        """Nama lengkap karyawan (untuk teks notifikasi)."""
        name: str | None = await self.scalar("SELECT full_name FROM vms.employee WHERE id = :id",
                                             {"id": str(employee_id)})
        return name
