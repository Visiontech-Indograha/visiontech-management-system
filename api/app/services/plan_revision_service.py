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
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChangeStatus, DocumentStatus, PlanStatus
from app.core.errors import AppError, NotFoundError, ValidationError, trigger_rule_error
from app.core.time import jakarta_now
from app.crud.crud_plan_change import CRUDPlanChange
from app.crud.crud_plan_revision import CRUDPlanRevision
from app.crud.crud_plan_transition import CRUDPlanTransition
from app.schemas.plan_revision import PlanRevisionIn
from app.services.notification_service import NotificationService
from app.services.plan_amendment_service import PlanAmendmentService
from app.services.plan_draft_service import PlanDraftService
from app.services.signature_service import ISSUER, SignatureService
from app.shared.access.access_service import PlanAccess

REVISABLE = (PlanStatus.PUBLISHED, PlanStatus.APPEALED, PlanStatus.ACCEPTED, PlanStatus.IN_PROGRESS)
NOT_ACCEPTED_YET = (PlanStatus.PUBLISHED, PlanStatus.APPEALED)
_FIELDS = (
    ("title", "Judul"),
    ("description", "Deskripsi"),
    ("category", "Kategori"),
    ("location_text", "Lokasi"),
    ("period_start", "Tanggal mulai"),
    ("period_end", "Tanggal selesai"),
    ("is_out_of_town", "Luar kota"),
)


def _names(snapshot: dict[str, Any], role: str) -> dict[str, str]:
    return {str(m["employee_id"]): str(m["full_name"]) for m in snapshot.get("team", []) if m["role_in_plan"] == role}


def _days(snapshot: dict[str, Any]) -> dict[str, list[str]]:
    """Isi tiap hari sebagai daftar penanda (tugas, lokasi hari itu, anggota hari itu) untuk mendeteksi perubahan."""
    return {
        str(d["work_date"]): [str(t["title"]) + "|" + str(t.get("description") or "") for t in d.get("tasks", [])]
        + [
            f"@lokasi|{d.get('site_name') or ''}",
            f"@anggota|{','.join(d.get('members') or [])}",
            f"@jenis|{d.get('work_type_name') or ''}",
        ]
        for d in snapshot.get("days", [])
    }


_MONTHS = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


def _fmt(d: date) -> str:
    return f"{d.day} {_MONTHS[d.month - 1]}"


def _work_days(snapshot: dict[str, Any], start: date, end_exclusive: date | None) -> int:
    """Jumlah hari kerja rencana (tanggal pada daftar hari) pada rentang [start, end_exclusive)."""
    return sum(
        1
        for d in snapshot.get("days", [])
        if date.fromisoformat(str(d["work_date"])) >= start
        and (end_exclusive is None or date.fromisoformat(str(d["work_date"])) < end_exclusive)
    )


def _joined(after: dict[str, Any], name: str, today: date) -> str:
    """Anggota baru berlaku mulai hari ini (atau awal rencana): "Andi (mulai 10 Okt, 3 hari kerja)"."""
    start = max(today, date.fromisoformat(str(after.get("plan", {}).get("period_start"))))
    return f"{name} (mulai {_fmt(start)}, {_work_days(after, start, None)} hari kerja)"


def _left(before: dict[str, Any], employee_id: str, name: str, today: date) -> str:
    """Hari kerja sejak anggota masuk sampai hari ini (tidak termasuk hari ini): "Budi (bekerja 2 hari kerja, ...)"."""
    since = next(
        (
            date.fromisoformat(str(m["since"]))
            for m in before.get("team", [])
            if str(m["employee_id"]) == employee_id and m.get("since")
        ),
        None,
    )
    if since is None:
        return name
    last = max(since, today)
    return f"{name} (bekerja {_work_days(before, since, today)} hari kerja, mulai {_fmt(since)}, keluar {_fmt(last)})"


def build_diff(before: dict[str, Any], after: dict[str, Any], today: date | None = None) -> list[dict[str, Any]]:
    """Daftar perubahan sebelum → sesudah; hanya yang berbeda. Anggota: added/removed; hari: added/removed/changed."""
    diff: list[dict[str, Any]] = []
    today = today or jakarta_now().date()
    b, a = before.get("plan", {}), after.get("plan", {})
    for key, label in _FIELDS:
        if b.get(key) != a.get(key):
            diff.append({"field": key, "label": label, "before": b.get(key), "after": a.get(key)})
    b_lead, a_lead = _names(before, "LEADER"), _names(after, "LEADER")
    if set(b_lead) != set(a_lead):
        diff.append(
            {
                "field": "leader",
                "label": "Ketua tim",
                "before": ", ".join(_left(before, i, n, today) for i, n in b_lead.items()) or None,
                "after": ", ".join(_joined(after, n, today) for n in a_lead.values()) or None,
            }
        )
    b_mem, a_mem = _names(before, "MEMBER"), _names(after, "MEMBER")
    if set(b_mem) != set(a_mem):
        diff.append(
            {
                "field": "members",
                "label": "Anggota",
                "added": [_joined(after, a_mem[i], today) for i in a_mem if i not in b_mem],
                "removed": [_left(before, i, b_mem[i], today) for i in b_mem if i not in a_mem],
            }
        )
    b_days, a_days = _days(before), _days(after)
    if b_days != a_days:
        diff.append(
            {
                "field": "days",
                "label": "Hari kerja",
                "added": sorted(set(a_days) - set(b_days)),
                "removed": sorted(set(b_days) - set(a_days)),
                "changed": sorted(d for d in set(a_days) & set(b_days) if a_days[d] != b_days[d]),
            }
        )
    b_assets = {str(x["code"]): str(x["name"]) for x in before.get("assets", [])}
    a_assets = {str(x["code"]): str(x["name"]) for x in after.get("assets", [])}
    if set(b_assets) != set(a_assets):
        diff.append(
            {
                "field": "assets",
                "label": "Alat & kendaraan",
                "added": [a_assets[i] for i in a_assets if i not in b_assets],
                "removed": [b_assets[i] for i in b_assets if i not in a_assets],
            }
        )
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
            raise AppError(
                "PLAN_NOT_REVISABLE",
                "Rencana kerja yang sudah selesai atau dibatalkan tidak bisa direvisi.",
                status=409,
            )
        reason = data.reason.strip()
        if not reason:
            raise ValidationError("Alasan revisi wajib diisi.")
        if plan.status == PlanStatus.IN_PROGRESS and data.period_start != plan.period_start:
            raise ValidationError("Tanggal mulai rencana kerja yang sedang berjalan tidak dapat diubah.")
        change = None
        if data.change_id is not None:
            change = await self.changes.lock_change(data.change_id, access.user.organization_id)
            if change is None or str(change.work_plan_id) != str(plan.id) or change.status != ChangeStatus.PENDING_PM:
                raise NotFoundError("Permintaan revisi")
        issuer = await self.amend._employee(access.user.user_id)
        await PlanDraftService(self.db)._validate(access.user, str(plan.unit_id), data, plan.id)

        before = await self._snapshot(plan.id)
        await self.amend.rewrite_days(plan, data, access.user)
        version = await self.changes.next_document_version(plan.id)
        try:
            await self.changes.apply_personnel(
                plan.id, str(data.leader_employee_id), [str(m) for m in data.member_employee_ids], version
            )
            allocated = await self.amend.repo.allocated_asset_ids(plan.id)
            for tool in data.tool_ids:
                if str(tool) not in allocated:
                    await self.amend.assets.insert_allocation(tool, plan.id, None, access.user.user_id)
                    await self.amend.assets.set_asset_status(tool, "IN_USE")
        except IntegrityError as exc:
            raise (
                trigger_rule_error(exc)
                or AppError("INVALID_STATE", "Jadwal bentrok dengan rencana kerja lain.", status=409)
            ) from None
        return await self._finish(access, plan, issuer, version, before, reason, change)

    async def _finish(
        self, access: PlanAccess, plan: Any, issuer: str, version: int, before: dict[str, Any], reason: str, change: Any
    ) -> Any:
        """Bagian bersama revisi PM dan perubahan lokasi: dokumen versi baru bertanda tangan PM, riwayat (diff),
        persetujuan otomatis permintaan ketua yang menunggu, dan pemberitahuan."""
        after = await self._snapshot(plan.id)
        diff = build_diff(before, after)
        if not diff:
            raise ValidationError("Tidak ada perubahan.")

        awaiting_leader = plan.status in NOT_ACCEPTED_YET
        await self.repo.supersede_awaiting(plan.id)
        if not awaiting_leader:
            await self.amend.repo.supersede_effective(plan.id, None)
        await self.repo.issue_revision_document(
            plan.id,
            version,
            after,
            issuer,
            reason,
            DocumentStatus.AWAITING_ACCEPTANCE if awaiting_leader else DocumentStatus.EFFECTIVE,
        )
        await SignatureService(self.db).sign_latest_plan_document(plan.id, issuer, ISSUER, access.user.user_id)
        if plan.status == PlanStatus.APPEALED:
            await self.plans.set_status(plan.id, PlanStatus.PUBLISHED)
            await self.repo.clear_appeal(plan.id)
        # Revisi PM = persetujuan: seluruh permintaan revisi ketua yang masih menunggu otomatis disetujui.
        pending = await self.changes.pending_amendment_ids(plan.id)
        for change_id in pending:
            await self.changes.set_change(change_id, ChangeStatus.EFFECTIVE, issuer, "Disetujui lewat revisi PM")
        if change is not None and str(change.id) not in pending:
            await self.changes.set_change(change.id, ChangeStatus.EFFECTIVE, issuer, "Disetujui lewat revisi PM")
        linked = str(change.id) if change is not None else (pending[0] if pending else None)
        await self.repo.insert_revision(access.user.organization_id, plan.id, version, issuer, reason, diff, linked)

        people = {str(m["employee_id"]) for m in [*before.get("team", []), *after.get("team", [])]}
        actor = await self.repo.employee_name(issuer) or "PM"
        await self.notify.plan_revised(plan.id, actor, reason, diff, people - {issuer})
        return await PlanDraftService(self.db).detail(plan.id)

    async def snapshot_of(self, plan_id: UUID | str) -> dict[str, Any]:
        """Isi dokumen saat ini (dipakai pemanggil sebelum mengubah sesuatu, lalu diteruskan ke `after_change`)."""
        return await self._snapshot(plan_id)

    async def after_change(self, access: PlanAccess, before: dict[str, Any], reason: str) -> None:
        """Perubahan di luar editor revisi (mis. lokasi) pada rencana yang sudah terbit → dokumen versi baru."""
        plan = access.plan
        issuer = await self.amend._employee(access.user.user_id)
        version = await self.changes.next_document_version(plan.id)
        await self._finish(access, plan, issuer, version, before, reason, None)
