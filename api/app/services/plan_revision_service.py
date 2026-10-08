"""
app/services/plan_revision_service.py
Revisi rencana kerja oleh PM kapan saja (Rencana Kerja v3, T6; keputusan pemilik 2026-10-08).

Alur: PM mengubah isi rencana kerja berstatus Terbit / Revisi diminta / Diterima / Berjalan → dokumen versi baru
ditandatangani PM otomatis → ketua dan anggota (lama dan baru) diberi tahu beserta diff sebelum/sesudah.
- Sesudah ketua menerima (Diterima/Berjalan): versi baru LANGSUNG berlaku, versi lama Tidak berlaku, ketua tidak
  menandatangani ulang.
- Sebelum ketua menerima (Terbit/Revisi diminta): versi baru terbit, ketua tetap menerima SEKALI (jawaban #2).
- Ketua boleh diganti: kewenangan mengikuti `work_plan.leader_employee_id`, jadi pindah hari itu juga.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChangeStatus, DocumentStatus, PlanStatus
from app.core.errors import AppError, NotFoundError, ValidationError, trigger_rule_error
from app.crud.crud_plan_change import CRUDPlanChange
from app.crud.crud_plan_revision import CRUDPlanRevision
from app.crud.crud_plan_transition import CRUDPlanTransition
from app.schemas.plan_revision import PlanRevisionIn
from app.services.access_service import PlanAccess
from app.services.notification_service import NotificationService
from app.services.plan_amendment_service import PlanAmendmentService
from app.services.plan_draft_service import PlanDraftService
from app.services.signature_service import ISSUER, SignatureService

REVISABLE = (PlanStatus.PUBLISHED, PlanStatus.APPEALED, PlanStatus.ACCEPTED, PlanStatus.IN_PROGRESS)
NOT_ACCEPTED_YET = (PlanStatus.PUBLISHED, PlanStatus.APPEALED)
_FIELDS = (("title", "Judul"), ("description", "Deskripsi"), ("category", "Kategori"),
           ("location_text", "Lokasi"), ("period_start", "Tanggal mulai"), ("period_end", "Tanggal selesai"),
           ("is_out_of_town", "Luar kota"))


def _names(snapshot: dict[str, Any], role: str) -> dict[str, str]:
    return {str(m["employee_id"]): str(m["full_name"]) for m in snapshot.get("team", []) if m["role_in_plan"] == role}


def _days(snapshot: dict[str, Any]) -> dict[str, list[str]]:
    return {str(d["work_date"]): [str(t["title"]) + "|" + str(t.get("description") or "") for t in d.get("tasks", [])]
            for d in snapshot.get("days", [])}


def build_diff(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """Daftar perubahan sebelum → sesudah; hanya yang berbeda. Anggota: added/removed; hari: added/removed/changed."""
    diff: list[dict[str, Any]] = []
    b, a = before.get("plan", {}), after.get("plan", {})
    for key, label in _FIELDS:
        if b.get(key) != a.get(key):
            diff.append({"field": key, "label": label, "before": b.get(key), "after": a.get(key)})
    b_lead, a_lead = _names(before, "LEADER"), _names(after, "LEADER")
    if set(b_lead) != set(a_lead):
        diff.append({"field": "leader", "label": "Ketua tim", "before": ", ".join(b_lead.values()) or None,
                     "after": ", ".join(a_lead.values()) or None})
    b_mem, a_mem = _names(before, "MEMBER"), _names(after, "MEMBER")
    if set(b_mem) != set(a_mem):
        diff.append({"field": "members", "label": "Anggota",
                     "added": [a_mem[i] for i in a_mem if i not in b_mem],
                     "removed": [b_mem[i] for i in b_mem if i not in a_mem]})
    b_days, a_days = _days(before), _days(after)
    if b_days != a_days:
        diff.append({"field": "days", "label": "Hari kerja",
                     "added": sorted(set(a_days) - set(b_days)), "removed": sorted(set(b_days) - set(a_days)),
                     "changed": sorted(d for d in set(a_days) & set(b_days) if a_days[d] != b_days[d])})
    b_assets = {str(x["asset_id"]): str(x["name"]) for x in before.get("assets", [])}
    a_assets = {str(x["asset_id"]): str(x["name"]) for x in after.get("assets", [])}
    if set(b_assets) != set(a_assets):
        diff.append({"field": "assets", "label": "Alat & kendaraan",
                     "added": [a_assets[i] for i in a_assets if i not in b_assets],
                     "removed": [b_assets[i] for i in b_assets if i not in a_assets]})
    return diff


class PlanRevisionService:
    """Layanan revisi rencana kerja oleh PM beserta riwayatnya."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDPlanRevision(db)
        self.changes = CRUDPlanChange(db)
        self.plans = CRUDPlanTransition(db)
        self.amend = PlanAmendmentService(db)
        self.notify = NotificationService(db)

    async def list_revisions(self, plan_id: UUID) -> list[Any]:
        return await self.repo.list_revisions(plan_id)

    async def _snapshot(self, plan_id: UUID | str) -> dict[str, Any]:
        raw = await self.plans.snapshot(plan_id)
        result: dict[str, Any] = json.loads(raw) if isinstance(raw, str) else raw
        return result

    async def revise_plan(self, access: PlanAccess, data: PlanRevisionIn) -> Any:
        """PM unit/OPS (dijaga router) merevisi rencana kerja. → detail rencana kerja pasca revisi."""
        plan = access.plan
        if plan.status not in REVISABLE:
            raise AppError("PLAN_NOT_REVISABLE",
                           "Rencana kerja yang sudah selesai atau dibatalkan tidak bisa direvisi.", status=409)
        reason = data.reason.strip()
        if not reason:
            raise ValidationError("Alasan revisi wajib diisi.")
        if plan.status == PlanStatus.IN_PROGRESS and data.period_start != plan.period_start:
            raise ValidationError("Tanggal mulai rencana kerja yang sedang berjalan tidak dapat diubah.")
        change = None
        if data.change_id is not None:
            change = await self.changes.lock_change(data.change_id, access.user.organization_id)
            if (change is None or str(change.work_plan_id) != str(plan.id)
                    or change.status != ChangeStatus.PENDING_PM):
                raise NotFoundError("Permintaan revisi")
        issuer = await self.amend._employee(access.user.user_id)
        await PlanDraftService(self.db)._validate(access.user, str(plan.unit_id), data, plan.id)

        before = await self._snapshot(plan.id)
        await self.amend.rewrite_days(plan, data, access.user)
        version = await self.changes.next_document_version(plan.id)
        try:
            await self.changes.apply_personnel(
                plan.id, str(data.leader_employee_id), [str(m) for m in data.member_employee_ids], version)
            allocated = await self.amend.repo.allocated_asset_ids(plan.id)
            for tool in data.tool_ids:
                if str(tool) not in allocated:
                    await self.amend.assets.insert_allocation(tool, plan.id, None, access.user.user_id)
                    await self.amend.assets.set_asset_status(tool, "IN_USE")
        except IntegrityError as exc:
            raise (trigger_rule_error(exc) or AppError(
                "INVALID_STATE", "Jadwal bentrok dengan rencana kerja lain.", status=409)) from None
        after = await self._snapshot(plan.id)
        diff = build_diff(before, after)
        if not diff:
            raise ValidationError("Tidak ada perubahan.")

        awaiting_leader = plan.status in NOT_ACCEPTED_YET
        await self.repo.supersede_awaiting(plan.id)
        if not awaiting_leader:
            await self.amend.repo.supersede_effective(plan.id, None)
        await self.repo.issue_revision_document(
            plan.id, version, after, issuer, reason,
            DocumentStatus.AWAITING_ACCEPTANCE if awaiting_leader else DocumentStatus.EFFECTIVE)
        await SignatureService(self.db).sign_latest_plan_document(plan.id, issuer, ISSUER, access.user.user_id)
        if plan.status == PlanStatus.APPEALED:
            await self.plans.set_status(plan.id, PlanStatus.PUBLISHED)
            await self.repo.clear_appeal(plan.id)
        if change is not None:
            await self.changes.set_change(change.id, ChangeStatus.EFFECTIVE, issuer, "Diterapkan lewat revisi PM")
        await self.repo.insert_revision(access.user.organization_id, plan.id, version, issuer, reason, diff,
                                        change.id if change is not None else None)

        people = {str(m["employee_id"]) for m in [*before.get("team", []), *after.get("team", [])]}
        actor = await self.repo.employee_name(issuer) or "PM"
        await self.notify.plan_revised(plan.id, actor, reason, diff, people - {issuer})
        return await PlanDraftService(self.db).detail(plan.id)
